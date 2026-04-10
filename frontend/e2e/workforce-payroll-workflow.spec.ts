import { e2eAuthenticatedGet, e2eAuthenticatedPost, expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";

function isoDateUtc(d: Date): string {
  return d.toISOString().slice(0, 10);
}

test.describe("workforce payroll full workflow", () => {
  test.setTimeout(240_000);

  test("create period → generate → adjustment → export CSV → approve → PDF → mark paid (owner)", async ({ page, authenticatedPage, authSession }) => {
    await authenticatedPage;

    const orgRole = authSession.orgs.find((o) => o.org_id === authSession.orgId)?.role;
    test.skip(orgRole === "VIEWER", "Payroll workflow requires editor or owner; viewers cannot create periods.");

    const suffix = `${Date.now()}`;
    const empRes = await e2eAuthenticatedPost(page, `${apiBase}/workforce/employees`, {
      org_id: authSession.orgId,
      first_name: "E2E",
      last_name: `Pay-${suffix}`,
      salary_type: "SALARIED",
      base_salary: "5000.00",
      employment_status: "ACTIVE",
    }, authSession);
    expect(empRes.ok(), await empRes.text()).toBeTruthy();
    const employee = (await empRes.json()) as { id: string };

    await page.goto("/app/workforce/payroll");
    // Periods + employees load in parallel; a 422 on employees can appear shortly after first paint.
    await expect(async () => {
      await expect(page.getByRole("heading", { name: "Payroll failed to load" })).toHaveCount(0);
      await expect(page.locator("main").getByRole("button", { name: "New period" })).toBeVisible();
    }).toPass({ timeout: 120_000 });

    const start = new Date();
    start.setUTCDate(start.getUTCDate() - 14);
    const end = new Date(start.getTime() + 6 * 86400000);

    await page.locator("main").getByRole("button", { name: "New period" }).click();
    const dialog = page.getByRole("dialog").filter({ has: page.locator('input[type="date"]') });
    await expect(dialog).toBeVisible({ timeout: 30_000 });
    await dialog.getByLabel("Start date").fill(isoDateUtc(start));
    await dialog.getByLabel("End date").fill(isoDateUtc(end));
    await dialog.getByRole("button", { name: "Create" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 60_000 });

    // Mutation sets activePeriodId before periods refetch finishes; toolbar can be empty briefly.
    const generateBtn = page.getByRole("button", { name: "Generate draft" });
    await expect(async () => {
      await expect(generateBtn).toBeVisible();
      await expect(generateBtn).toBeEnabled();
    }).toPass({ timeout: 90_000 });
    const generateDone = page.waitForResponse(
      (r) =>
        r.request().method() === "POST" &&
        r.url().includes("/workforce/payroll/periods/") &&
        r.url().includes("/generate") &&
        r.ok(),
      { timeout: 120_000 },
    );
    await generateBtn.click({ force: true });
    const generateRes = await generateDone;
    const payrollEntries = (await generateRes.json()) as Array<{ id: string; employee_id: string }>;
    const payrollEntry = payrollEntries.find((e) => e.employee_id === employee.id);
    expect(payrollEntry, "generate should return an entry for the E2E employee").toBeTruthy();

    await expect(page.getByText(`Pay-${suffix}`, { exact: false }).first()).toBeVisible({ timeout: 120_000 });

    await page.locator("main").getByPlaceholder("Amount").fill("50");
    const adjustmentDone = page.waitForResponse(
      (r) =>
        r.request().method() === "POST" &&
        r.url().includes("/workforce/payroll/adjustments") &&
        r.ok(),
      { timeout: 60_000 },
    );
    await page.locator("main").getByRole("button", { name: "Add" }).click();
    await adjustmentDone;
    await expect(page.getByText("BONUS").first()).toBeVisible({ timeout: 30_000 });

    const exportDone = page.waitForResponse(
      (r) =>
        r.request().method() === "GET" &&
        r.url().includes("/workforce/payroll/periods/") &&
        r.url().includes("/export") &&
        r.ok(),
      { timeout: 60_000 },
    );
    await page.getByRole("button", { name: "Export CSV" }).click();
    const exportRes = await exportDone;
    const csvText = await exportRes.text();
    expect(csvText.length).toBeGreaterThan(20);
    expect(csvText).toContain(employee.id);

    await page.getByRole("button", { name: "Approve" }).click({ force: true });
    await expect(page.getByText(/· APPROVED/)).toBeVisible({ timeout: 60_000 });

    await page.getByRole("button", { name: "Download PDF" }).click({ force: true });

    // Attachment PDF fetch often yields an empty body on the page Response; assert bytes via API request.
    const pdfRes = await e2eAuthenticatedGet(
      page,
      `${apiBase}/workforce/payroll/entries/${payrollEntry!.id}/payslip/pdf?org_id=${encodeURIComponent(authSession.orgId)}`,
      authSession,
    );
    expect(pdfRes.ok(), await pdfRes.text()).toBeTruthy();
    const pdfBytes = await pdfRes.body();
    expect(Buffer.from(pdfBytes).subarray(0, 4).toString("utf8")).toBe("%PDF");

    if (orgRole === "OWNER") {
      const markPaidDone = page.waitForResponse(
        (r) =>
          r.request().method() === "POST" &&
          r.url().includes("/workforce/payroll/periods/") &&
          r.url().includes("/mark-paid") &&
          r.ok(),
        { timeout: 60_000 },
      );
      await page.getByRole("button", { name: "Mark paid" }).click({ force: true });
      await markPaidDone;
      await expect(page.getByText(/· PAID/)).toBeVisible({ timeout: 60_000 });
    } else if (orgRole === "EDITOR") {
      await expect(page.getByRole("button", { name: "Mark paid" })).toHaveCount(0);
      await expect(page.getByText("Only an owner can mark this period as paid.")).toBeVisible();
    }
  });
});
