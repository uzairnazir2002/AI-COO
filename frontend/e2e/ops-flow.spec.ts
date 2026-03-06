import { expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";

test("registration routes to confirmation page", async ({ page }) => {
  const namespace = `confirm-${Date.now()}`;
  await page.goto("/auth/register");
  await page.getByPlaceholder("Email").fill(`confirm_${namespace}@example.com`);
  await page.getByPlaceholder("Password (min 8 chars)").fill("Password123!");
  await page.getByRole("button", { name: /Create account/i }).click();
  await expect(page).toHaveURL(/\/auth\/confirm\?email=/);
  await expect(page.getByRole("heading", { name: "Activate your access" })).toBeVisible();
});

test("confirmation page shows backend failure for invalid token", async ({ page }) => {
  await page.goto("/auth/confirm");
  await page.getByPlaceholder("Confirmation token").fill("invalid-token");
  await page.getByRole("button", { name: /Confirm account/i }).click();
  await expect(page.getByText(/invalid|expired/i)).toBeVisible();
});

test("invite acceptance flow creates a usable account", async ({ page, authSession, authenticatedPage }) => {
  test.skip(authSession.authMode !== "bearer", "Invite acceptance helper currently relies on bearer-mode request auth.");
  await authenticatedPage;

  const inviteEmail = `invite_${authSession.namespace}@example.com`;
  const invitePassword = "Password123!";
  const inviteRes = await page.request.post(`${apiBase}/organizations/${authSession.orgId}/invite`, {
    data: { email: inviteEmail, role: "VIEWER" },
    headers: { Authorization: `Bearer ${authSession.accessToken}` },
  });
  expect(inviteRes.ok(), await inviteRes.text()).toBeTruthy();
  const inviteJson = (await inviteRes.json()) as { invite_token?: string };
  expect(inviteJson.invite_token).toBeTruthy();

  const invitePage = await page.context().newPage();
  await invitePage.goto(`/auth/register?invite_token=${inviteJson.invite_token}`);
  await expect(invitePage.getByRole("heading", { name: "Join your organization" })).toBeVisible();
  await invitePage.getByPlaceholder("Password (min 8 chars)").fill(invitePassword);
  await invitePage.getByRole("button", { name: /Accept invite/i }).click();
  await invitePage.waitForURL(/\/auth\/login/);
  await invitePage.getByLabel("Email").fill(inviteEmail);
  await invitePage.getByLabel("Password").fill(invitePassword);
  await invitePage.getByRole("button", { name: /Sign in/i }).click();
  await invitePage.waitForURL(/\/(app\/(dashboard|orgs)|dashboard)/, { timeout: 30000 });
});

test("activity page exposes outbox and scheduler admin sections for owners", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/activity");
  await expect(page.getByRole("heading", { name: "Activity" })).toBeVisible();
  await expect(page.getByText("Outbox monitor")).toBeVisible();
  await expect(page.getByText("Scheduler admin")).toBeVisible();
});

test("top-level protected aliases render without redirect-only route loss", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByRole("heading", { name: "Executive dashboard" })).toBeVisible();

  await page.goto("/activity");
  await expect(page).toHaveURL(/\/activity/);
  await expect(page.getByRole("heading", { name: "Activity" })).toBeVisible();
});
