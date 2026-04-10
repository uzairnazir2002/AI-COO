import { expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";
const inviteRetryAttempts = Math.max(1, Number(process.env.E2E_INVITE_RETRY_ATTEMPTS || 3));
const inviteRetryDelayMs = Math.max(100, Number(process.env.E2E_INVITE_RETRY_DELAY_MS || 600));

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

test("viewer bearer session cannot create transactions (403)", async ({ page, authSession }) => {
  test.skip(authSession.authMode !== "bearer", "RBAC API check uses Bearer Authorization; skip in cookie auth mode.");

  const inviteEmail = `rbac_viewer_${authSession.namespace}@example.com`;
  const invitePassword = "Password123!";
  let inviteRes: Awaited<ReturnType<typeof page.request.post>> | null = null;
  let lastTransportError: unknown = null;

  for (let attempt = 1; attempt <= inviteRetryAttempts; attempt += 1) {
    try {
      inviteRes = await page.request.post(`${apiBase}/organizations/${authSession.orgId}/invite`, {
        data: { email: inviteEmail, role: "VIEWER" },
        headers: { Authorization: `Bearer ${authSession.accessToken}` },
      });
      if (inviteRes.ok()) break;
      const shouldRetry = inviteRes.status() === 429 || inviteRes.status() >= 500;
      if (!shouldRetry || attempt === inviteRetryAttempts) break;
    } catch (error) {
      lastTransportError = error;
      if (attempt === inviteRetryAttempts) break;
    }
    await delay(inviteRetryDelayMs * attempt);
  }
  if (!inviteRes && lastTransportError) {
    throw lastTransportError;
  }
  expect(inviteRes, "invite response was not created").toBeTruthy();
  expect(inviteRes!.ok(), await inviteRes!.text()).toBeTruthy();
  const inviteJson = (await inviteRes!.json()) as { invite_token?: string };
  expect(inviteJson.invite_token).toBeTruthy();

  const invitePage = await page.context().newPage();
  await invitePage.goto(`/auth/register?invite_token=${inviteJson.invite_token}`);
  await expect(invitePage.getByRole("heading", { name: "Join your organization" })).toBeVisible();
  await invitePage.getByPlaceholder("Password (min 8 chars)").fill(invitePassword);
  await invitePage.getByRole("button", { name: /Accept invite/i }).click();
  await invitePage.waitForURL(/\/auth\/login/);
  await invitePage.close();

  const loginRes = await page.request.post(`${apiBase}/auth/login`, {
    data: { email: inviteEmail, password: invitePassword },
  });
  expect(loginRes.ok(), await loginRes.text()).toBeTruthy();
  const loginJson = (await loginRes.json()) as { access_token?: string | null };
  const viewerToken = loginJson.access_token;
  expect(viewerToken).toBeTruthy();

  const createRes = await page.request.post(`${apiBase}/transactions`, {
    data: {
      org_id: authSession.orgId,
      date: "2026-04-08",
      amount: "1.00",
      type: "REVENUE",
      category: "rbac-e2e",
    },
    headers: { Authorization: `Bearer ${viewerToken}` },
  });
  expect(createRes.status(), await createRes.text()).toBe(403);
});
