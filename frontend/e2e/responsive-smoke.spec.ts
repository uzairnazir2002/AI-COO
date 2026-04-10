import { expect, test } from "./fixtures/auth";

test.describe("responsive shell (tablet viewport)", () => {
  /** Top-level viewport for this describe so `authenticatedPage` runs at tablet width (fixtures run before test body). */
  test.use({ viewport: { width: 834, height: 1112 } });

  test("dashboard loads and primary actions remain reachable", async ({ page, authenticatedPage }) => {
    await authenticatedPage;
    await expect(page.getByLabel("Organization switcher")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByRole("heading", { name: /Executive dashboard/i })).toBeVisible();
    /** Use the primary nav link inside the shell sidebar (not `.first()` — dashboard may duplicate route CTAs). */
    const forecastLink = page.locator("aside").locator('a[href="/app/forecast"]').first();
    await expect(forecastLink).toBeVisible();
    // Some tablet layouts render a scrollable sidebar where the link can be outside Playwright's viewport heuristics.
    await forecastLink.evaluate((node) => (node as HTMLAnchorElement).click());
    await expect(page).toHaveURL(/\/app\/forecast/);
  });
});
