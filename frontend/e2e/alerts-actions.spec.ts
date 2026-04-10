import { expect, test } from "./fixtures/auth";

test("alerts actions: open feed allows dismiss (owner/editor)", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/alerts", { waitUntil: "domcontentloaded" });
  await expect(page.locator("h1", { hasText: "Alerts" })).toBeVisible();

  // Ensure we have an alert to act on; otherwise this test is not meaningful.
  const quiet = await page.getByText("No alerts in this view.").count();
  test.skip(quiet > 0, "No alerts available to dismiss in this environment.");

  // Open first alert (works in both simple and advanced layouts).
  const firstAlert = page.getByRole("button", { name: /open alert|alert/i }).first();
  if (await firstAlert.count()) {
    await firstAlert.click();
  } else {
    // Fallback: click first visible alert card container
    await page.locator("button").filter({ hasText: /ANOMALY|RUNWAY|PROFIT_LEAK/i }).first().click();
  }

  // Dismiss (should be available for owner/editor; for viewer it'll be disabled)
  const dismissButton = page.getByRole("button", { name: "Dismiss" }).first();
  await expect(dismissButton).toBeVisible({ timeout: 30_000 });
  await dismissButton.click();
  await expect(page.getByText(/Alert dismissed/i)).toBeVisible({ timeout: 30_000 });
});

