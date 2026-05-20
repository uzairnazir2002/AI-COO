import { expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";

test("workforce RBAC negative: viewer cannot mutate and cross-org is blocked", async ({ page, authSession }) => {
  test.skip(authSession.authMode !== "bearer", "RBAC API check requires bearer mode.");
  const ownerHeaders = { Authorization: `Bearer ${authSession.accessToken}`, "X-Org-Id": authSession.orgId };

  const suffix = `${Date.now()}`;

  const inviteRes = await page.request.post(`${apiBase}/organizations/${authSession.orgId}/invite`, {
    data: { email: `workforce_viewer_${authSession.namespace}@example.com`, role: "VIEWER" },
    headers: ownerHeaders,
  });
  expect(inviteRes.ok(), await inviteRes.text()).toBeTruthy();
  const inviteJson = (await inviteRes.json()) as { invite_token?: string };
  expect(inviteJson.invite_token).toBeTruthy();

  const invitePage = await page.context().newPage();
  await invitePage.goto(`/auth/register?invite_token=${inviteJson.invite_token}`);
  await invitePage.getByPlaceholder("Password (min 8 chars)").fill("Password123!");
  await invitePage.getByRole("button", { name: /Accept invite/i }).click();
  await invitePage.waitForURL(/\/auth\/login/);
  await invitePage.close();

  const viewerEmail = `workforce_viewer_${authSession.namespace}@example.com`;
  const loginRes = await page.request.post(`${apiBase}/auth/login`, {
    data: { email: viewerEmail, password: "Password123!" },
  });
  expect(loginRes.ok(), await loginRes.text()).toBeTruthy();
  const viewerToken = ((await loginRes.json()) as { access_token?: string }).access_token;
  expect(viewerToken).toBeTruthy();
  const viewerHeaders = { Authorization: `Bearer ${viewerToken}`, "X-Org-Id": authSession.orgId };

  const empRes = await page.request.post(`${apiBase}/workforce/employees`, {
    data: { first_name: "RBAC", last_name: `Owner-${suffix}`, employment_status: "ACTIVE", salary_type: "SALARIED" },
    headers: ownerHeaders,
  });
  expect(empRes.ok(), await empRes.text()).toBeTruthy();
  const employee = (await empRes.json()) as { id: string };

  const mutationChecks: Array<Promise<any>> = [
    page.request.post(`${apiBase}/workforce/departments`, { data: { name: `D-${suffix}` }, headers: viewerHeaders }),
    page.request.post(`${apiBase}/workforce/titles`, { data: { name: `T-${suffix}` }, headers: viewerHeaders }),
    page.request.post(`${apiBase}/workforce/employees`, {
      data: { first_name: "No", last_name: "Write", employment_status: "ACTIVE", salary_type: "SALARIED" },
      headers: viewerHeaders,
    }),
    page.request.post(`${apiBase}/workforce/attendance/clock-in`, {
      data: { employee_id: employee.id, date: "2026-05-05", check_in_at: "2026-05-05T09:00:00Z" },
      headers: viewerHeaders,
    }),
    page.request.post(`${apiBase}/workforce/leave/types`, {
      data: { name: `L-${suffix}`, code: `L${suffix.slice(-4)}`, is_paid: true, requires_approval: true },
      headers: viewerHeaders,
    }),
    page.request.post(`${apiBase}/workforce/payroll/periods`, {
      data: { start_date: "2026-05-01", end_date: "2026-05-31" },
      headers: viewerHeaders,
    }),
    page.request.post(`${apiBase}/workforce/announcements`, {
      data: { title: `A-${suffix}`, body: "viewer blocked", priority: "NORMAL" },
      headers: viewerHeaders,
    }),
    page.request.post(`${apiBase}/workforce/hr/policies`, {
      data: { code: `P${suffix.slice(-6)}`, title: "Policy", body: "viewer blocked", requires_ack: true },
      headers: viewerHeaders,
    }),
  ];

  const results = await Promise.all(mutationChecks);
  for (const res of results) {
    expect(res.status(), await res.text()).toBe(403);
  }

  const wrongOrg = crypto.randomUUID();
  const crossOrg = await page.request.get(`${apiBase}/workforce/employees?org_id=${authSession.orgId}`, {
    headers: { Authorization: `Bearer ${viewerToken}`, "X-Org-Id": wrongOrg },
  });
  expect(crossOrg.status(), await crossOrg.text()).toBe(403);
});

