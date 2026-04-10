import { expect, test } from "./fixtures/auth";

/**
 * For accurate results, run Playwright with the managed web server (not a stale external origin):
 * - Do not set `E2E_USE_EXTERNAL_BASE_URL=1` unless the server matches this build.
 * - Prefer `E2E_BASE_URL=http://localhost:3001` (see `playwright.config.ts`; repo `.env` may use :3000 for Docker).
 */
process.env.E2E_FORCE_VIEWPORT = "390x844";

test.use({ viewport: { width: 390, height: 844 } });

test("mobile shell: opens slide-out nav and navigates to Money", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  /** `authenticatedPage` already lands on `/app/dashboard`. */
  await expect(page.getByLabel("Organization switcher")).toBeVisible({ timeout: 60_000 });
  await page.getByRole("button", { name: "Open navigation menu" }).click();
  const moneyLink = page.locator('a[href="/app/transactions"]');
  await expect(moneyLink.first()).toBeVisible();
  await moneyLink.first().click();
  await expect(page).toHaveURL(/\/app\/transactions/);
});
