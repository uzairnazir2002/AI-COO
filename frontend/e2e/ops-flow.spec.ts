import { expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";
const inviteRetryAttempts = Math.max(1, Number(process.env.E2E_INVITE_RETRY_ATTEMPTS || 3));
const inviteRetryDelayMs = Math.max(100, Number(process.env.E2E_INVITE_RETRY_DELAY_MS || 600));

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

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
  if (!inviteRes!.ok()) {
    expect(inviteRes!.ok(), await inviteRes!.text()).toBeTruthy();
  }
  const inviteJson = (await inviteRes!.json()) as { invite_token?: string };
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

test("activity page handles owner admin operations by role", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/activity");
  await expect(page.getByRole("heading", { name: "Activity" })).toBeVisible();
  const ownerControlsVisible = (await page.getByText("Security & compliance").count()) > 0;
  if (ownerControlsVisible) {
    await expect(page.getByText("Security & compliance")).toBeVisible();
    await expect(page.getByRole("button", { name: "Download audit NDJSON" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Rotate organization PII" })).toBeVisible();
    await expect(page.getByText("Outbox monitor")).toBeVisible();
    await expect(page.getByText("Scheduler admin")).toBeVisible();
  } else {
    await expect(page.getByText("Security & compliance")).toHaveCount(0);
    await expect(page.getByText("Outbox monitor")).toHaveCount(0);
    await expect(page.getByText("Scheduler admin")).toHaveCount(0);
  }
});

test("settings page exposes deletion request controls", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/settings");
  await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  await expect(page.getByText("Data & compliance actions")).toBeVisible();
  await expect(page.getByRole("button", { name: "Request account deletion" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Request organization deletion" })).toBeVisible();
  const ownerPolicyVisible = (await page.getByText("Owner security policy").count()) > 0;
  if (ownerPolicyVisible) {
    await expect(page.getByText("Owner security policy")).toBeVisible();
    await expect(page.getByLabel("Require MFA for all owners")).toBeVisible();
    await expect(page.getByRole("button", { name: "Save owner policy" })).toBeVisible();
    await expect(page.getByText("Sensitive action re-auth")).toBeVisible();
  }
});

test("top-level protected aliases render without redirect-only route loss", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByRole("heading", { name: "Executive dashboard" })).toBeVisible();

  await page.goto("/activity");
  await expect(page).toHaveURL(/\/activity/);
  await expect(page).not.toHaveURL(/\/auth\/login/);
  await expect(page.getByRole("button", { name: "Open notifications" })).toBeVisible();
});

test("login succeeds when return_to context is present", async ({ page, authenticatedPage, authSession }) => {
  await authenticatedPage;
  await page.goto("/auth/login?return_to=%2Fapp%2Factivity");
  await expect(page).toHaveURL(/\/auth\/login\?return_to=/);
  await page.getByLabel("Email").fill(authSession.email);
  await page.getByLabel("Password").fill(authSession.password);
  await page.getByRole("button", { name: /Sign in/i }).click();
  await page.waitForURL(/\/app\/(activity|dashboard|orgs)/, { timeout: 30000 });
  await expect(page).not.toHaveURL(/\/auth\/login/);
});
