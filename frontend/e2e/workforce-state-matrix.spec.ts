import { expect, test } from "./fixtures/auth";

const routes = [
  { path: "/app/workforce/employees", errorTitle: /Employees failed to load/i, emptyHint: /No employees/i },
  { path: "/app/workforce/attendance", errorTitle: /Attendance failed to load/i, emptyHint: /No attendance records/i },
  { path: "/app/workforce/leave", errorTitle: /Leave failed to load/i, emptyHint: /No pending leave requests|No calendar data|No leave history/i },
  { path: "/app/workforce/payroll", errorTitle: /Payroll failed to load/i, emptyHint: /No payroll periods|Select a payroll period/i },
  { path: "/app/workforce/communications", errorTitle: /Communications failed to load/i, emptyHint: /No announcements/i },
  { path: "/app/workforce/hr", errorTitle: /HR admin failed to load|HR failed to load/i, emptyHint: /No policies|No checklist items|No documents/i },
];

test.describe("workforce state matrix", () => {
  test("route error states render when workforce API fails", async ({ page, authenticatedPage }) => {
    await authenticatedPage;
    await page.route("**/api/v1/workforce/**", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "forced error for state test" }),
        });
        return;
      }
      await route.continue();
    });

    for (const routeCase of routes) {
      await page.goto(routeCase.path);
      await expect(page.getByRole("heading", { name: routeCase.errorTitle })).toBeVisible();
      await expect(page.getByRole("button", { name: /retry/i })).toBeVisible();
    }
  });

  test("viewer sees permission-limited states on mutate surfaces", async ({ page, authenticatedPage, authSession }) => {
    await authenticatedPage;
    const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";
    const meRes = await page.request.get(`${apiBase}/auth/me`, {
      headers: authSession.accessToken ? { Authorization: `Bearer ${authSession.accessToken}` } : undefined,
    });
    expect(meRes.ok(), await meRes.text()).toBeTruthy();
    const mePayload = (await meRes.json()) as { orgs: Array<{ org_id: string; role: string; name: string }> } & Record<string, unknown>;
    mePayload.orgs = (mePayload.orgs || []).map((org) => (org.org_id === authSession.orgId ? { ...org, role: "VIEWER" } : org));

    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mePayload),
      });
    });

    const mutateRoutes: Array<{ path: string; marker: RegExp }> = [
      { path: "/app/workforce/attendance", marker: /read-only access/i },
      { path: "/app/workforce/leave", marker: /read-only access/i },
      { path: "/app/workforce/payroll", marker: /read-only access/i },
      { path: "/app/workforce/communications", marker: /read-only access/i },
      { path: "/app/workforce/hr", marker: /read-only access/i },
    ];
    for (const routeCase of mutateRoutes) {
      await page.goto(routeCase.path);
      await expect(page.getByText(routeCase.marker).first(), `permission state missing on ${routeCase.path}`).toBeVisible();
    }
  });
});
