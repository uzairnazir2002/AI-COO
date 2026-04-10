import { expect, test } from "@playwright/test";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

test.describe("auth confirm page (UI)", () => {
  test("shows activation form and surfaces error for bogus token", async ({ page }) => {
    await page.goto("/auth/confirm");
    await expect(page.getByRole("heading", { name: /Activate your access/i })).toBeVisible();
    await expect(page.getByPlaceholder("Confirmation token")).toBeVisible();
    await page.getByPlaceholder("Confirmation token").fill("e2e-invalid-token-not-real");
    await page.getByRole("button", { name: /Confirm account/i }).click();
    await expect(page.locator(".text-danger").first()).toBeVisible({ timeout: 30_000 });
  });

  test("happy path: register → dev token → confirm UI → login", async ({ page, request }, testInfo) => {
    const probe = await request.get(`${apiBase}/auth/dev/confirmation-token`, {
      params: { email: "e2e-probe@example.com" },
    });
    test.skip(probe.status() === 404, "dev confirmation token route unavailable (non-development backend)");

    const ns = `${Date.now()}-w${testInfo.workerIndex}`;
    const email = `e2e_confirm_ui_${ns}@example.com`;
    const password = "Password123!";

    const reg = await request.post(`${apiBase}/auth/register`, { data: { email, password } });
    expect(reg.ok(), await reg.text()).toBeTruthy();

    let token: string | null = null;
    for (let i = 0; i < 30; i += 1) {
      const tr = await request.get(`${apiBase}/auth/dev/confirmation-token`, { params: { email } });
      expect(tr.ok(), await tr.text()).toBeTruthy();
      const body = (await tr.json()) as { token?: string | null; found?: boolean };
      if (body.found && body.token) {
        token = body.token;
        break;
      }
      await delay(400);
    }
    expect(token, "confirmation token not found in dev outbox after register").toBeTruthy();

    await page.goto("/auth/confirm", { waitUntil: "domcontentloaded" });
    await page.getByPlaceholder("Confirmation token").fill(token!);
    await Promise.all([
      page.waitForURL(/\/auth\/login/, { timeout: 60_000, waitUntil: "domcontentloaded" }),
      page.getByRole("button", { name: /Confirm account/i }).click(),
    ]);

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: /Sign in/i }).click();
    await page.waitForURL(/\/app\/(dashboard|orgs)/, { timeout: 30_000 });
  });
});
