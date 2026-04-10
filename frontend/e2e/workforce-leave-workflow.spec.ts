import { e2eAuthenticatedPost, expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";

test.describe("workforce leave workflow", () => {
  test.setTimeout(180_000);

  test("allocate → request → approve → calendar shows leave", async ({ page, authenticatedPage, authSession }) => {
    await authenticatedPage;

    const orgRole = authSession.orgs.find((o) => o.org_id === authSession.orgId)?.role;
    test.skip(orgRole === "VIEWER", "Leave workflow requires editor or owner.");

    const suffix = `${Date.now()}`;
    const empRes = await e2eAuthenticatedPost(page, `${apiBase}/workforce/employees`, {
      org_id: authSession.orgId,
      first_name: "E2E",
      last_name: `Lv-${suffix}`,
      salary_type: "SALARIED",
      base_salary: "5000.00",
      employment_status: "ACTIVE",
    }, authSession);
    expect(empRes.ok(), await empRes.text()).toBeTruthy();
    const employee = (await empRes.json()) as { id: string };

    const ltRes = await e2eAuthenticatedPost(page, `${apiBase}/workforce/leave/types`, {
      org_id: authSession.orgId,
      name: `E2E PTO ${suffix}`,
      code: `E${suffix}`.slice(0, 40),
      is_paid: true,
      requires_approval: true,
      is_active: true,
    }, authSession);
    expect(ltRes.ok(), await ltRes.text()).toBeTruthy();
    const leaveType = (await ltRes.json()) as { id: string };

    const year = new Date().getFullYear();
    const start = `${year}-06-15`;
    const end = `${year}-06-16`;

    const allocRes = await e2eAuthenticatedPost(page, `${apiBase}/workforce/leave/balances/allocate`, {
      org_id: authSession.orgId,
      employee_id: employee.id,
      leave_type_id: leaveType.id,
      year,
      allocated_days: "10",
    }, authSession);
    expect(allocRes.ok(), await allocRes.text()).toBeTruthy();

    await page.goto("/app/workforce/leave");
    await expect(async () => {
      await expect(page.getByRole("heading", { name: "Leave failed to load" })).toHaveCount(0);
      await expect(page.getByRole("heading", { name: "Leave", exact: true })).toBeVisible();
      await expect(page.getByRole("button", { name: "Submit request" })).toBeVisible();
    }).toPass({ timeout: 120_000 });

    const requestCard = page
      .getByRole("heading", { name: "Request leave" })
      .locator("xpath=ancestor::div[contains(@class,'glass-panel')][1]");

    await requestCard.getByRole("combobox").nth(0).click();
    await page.getByRole("option", { name: new RegExp(`Lv-${suffix}`) }).click();

    await requestCard.getByRole("combobox").nth(1).click();
    await page.getByRole("option", { name: new RegExp(`E2E PTO ${suffix}`) }).click();

    const dateInputs = requestCard.locator('input[type="date"]');
    await dateInputs.nth(0).fill(start);
    await dateInputs.nth(1).fill(end);
    await requestCard.locator('input[inputmode="decimal"]').fill("2");

    const createWait = page.waitForResponse(
      (r) =>
        r.request().method() === "POST" &&
        r.url().includes("/workforce/leave/requests") &&
        !r.url().includes("/decision") &&
        r.ok(),
      { timeout: 60_000 },
    );
    await page.getByRole("button", { name: "Submit request" }).click();
    await createWait;

    await expect(page.getByRole("tab", { name: "Approvals" })).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText(new RegExp(`Lv-${suffix}`)).first()).toBeVisible();

    const decisionWait = page.waitForResponse(
      (r) => r.request().method() === "POST" && r.url().includes("/decision") && r.ok(),
      { timeout: 60_000 },
    );
    await page.getByRole("button", { name: "Approve" }).click();
    await decisionWait;

    await expect(page.getByRole("heading", { name: "No pending leave requests." })).toBeVisible();

    await page.getByRole("tab", { name: "Calendar" }).click();
    await page.locator('input[type="month"]').fill(start.slice(0, 7));
    await expect(page.getByText("1 employee(s) on leave").first()).toBeVisible({ timeout: 30_000 });
  });
});
