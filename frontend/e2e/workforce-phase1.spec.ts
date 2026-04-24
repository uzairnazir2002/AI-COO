import { e2eAuthenticatedGet, e2eAuthenticatedPost, expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";

test.describe("workforce phase 1: employees + org structure", () => {
  test.setTimeout(180_000);

  test("create department + title + employee, then filter/search employee directory", async ({ page, authenticatedPage, authSession }) => {
    await authenticatedPage;

    const orgRole = authSession.orgs.find((o) => o.org_id === authSession.orgId)?.role;
    test.skip(orgRole === "VIEWER", "Employee creation requires editor or owner.");

    const suffix = `${Date.now()}`;

    async function postWithRetry<T>(url: string, body: T) {
      let lastErr: unknown = null;
      for (let i = 0; i < 3; i++) {
        try {
          const res = await e2eAuthenticatedPost(page, url, body as Record<string, unknown>, authSession);
          if (res.ok()) return res;
          lastErr = await res.text();
        } catch (err) {
          lastErr = err;
        }
        await page.waitForTimeout(1500);
      }
      throw new Error(`POST failed after retries: ${url} (${String(lastErr)})`);
    }

    const deptRes = await postWithRetry(`${apiBase}/workforce/departments`, {
      org_id: authSession.orgId,
      name: `E2E Dept ${suffix}`,
      code: `D${suffix}`.slice(0, 40),
    });
    expect(deptRes.ok(), await deptRes.text()).toBeTruthy();
    const dept = (await deptRes.json()) as { id: string };

    const titleRes = await postWithRetry(`${apiBase}/workforce/titles`, {
      org_id: authSession.orgId,
      name: `E2E Title ${suffix}`,
      level: 3,
    });
    expect(titleRes.ok(), await titleRes.text()).toBeTruthy();
    const title = (await titleRes.json()) as { id: string };

    const empRes = await postWithRetry(`${apiBase}/workforce/employees`, {
      org_id: authSession.orgId,
      first_name: "E2E",
      last_name: `Emp-${suffix}`,
      department_id: dept.id,
      title_id: title.id,
      salary_type: "SALARIED",
      base_salary: "5000.00",
      employment_status: "ACTIVE",
    });
    expect(empRes.ok(), await empRes.text()).toBeTruthy();
    const employee = (await empRes.json()) as { id: string };

    await page.goto("/app/workforce/employees");
    await expect(async () => {
      await expect(page.getByRole("heading", { name: "Employees failed to load" })).toHaveCount(0);
      await expect(page.getByRole("heading", { name: "Employees", exact: true })).toBeVisible();
    }).toPass({ timeout: 120_000 });

    await page.getByPlaceholder("Search name, email, or employee code").fill(`Emp-${suffix}`);
    await expect(page.getByText(`Emp-${suffix}`, { exact: false }).first()).toBeVisible({ timeout: 60_000 });

    // Filter by department (Radix Select renders a combobox button that contains the selected text).
    const deptSelect = page.getByRole("combobox").filter({ hasText: "All departments" }).first();
    const deptOption = page.getByRole("option", { name: new RegExp(`E2E Dept ${suffix}`) });
    await expect(async () => {
      await deptSelect.click();
      await expect(deptOption).toBeVisible();
      await deptOption.click();
    }).toPass({ timeout: 30_000 });
    await expect(page.getByText(`Emp-${suffix}`, { exact: false }).first()).toBeVisible({ timeout: 30_000 });

    // Ensure employee detail loads
    await page.getByText(`Emp-${suffix}`, { exact: false }).first().click();
    await expect(page.getByText("Employee profile")).toBeVisible({ timeout: 60_000 });

    // Viewers should see redacted compensation; verify via API when viewer role.
    if (orgRole === "VIEWER") {
      const getRes = await e2eAuthenticatedGet(
        page,
        `${apiBase}/workforce/employees/${employee.id}?org_id=${encodeURIComponent(authSession.orgId)}`,
        authSession,
      );
      expect(getRes.ok(), await getRes.text()).toBeTruthy();
      const body = (await getRes.json()) as { base_salary: string | null; hourly_rate: string | null };
      expect(body.base_salary).toBeNull();
      expect(body.hourly_rate).toBeNull();
    }
  });
});

