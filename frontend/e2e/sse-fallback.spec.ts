import { expect, test } from "./fixtures/auth";

test("SSE fallback activates and recovers to live", async ({ page, authenticatedPage }) => {
  test.skip(process.env.E2E_SSE !== "1", "SSE fallback spec runs only when E2E_SSE=1");
  await authenticatedPage;

  let forceFail = true;
  await page.route("**/api/v1/events/stream**", async (route) => {
    if (forceFail) {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "forced stream failure" }),
      });
      return;
    }
    await route.continue();
  });

  await page.goto("/app/dashboard");

  await page.getByRole("button", { name: "Open notifications" }).click();
  await expect(page.getByText(/Stream status: fallback polling\./i)).toBeVisible({ timeout: 25000 });

  forceFail = false;
  await expect(page.getByText(/Stream status: live\./i)).toBeVisible({ timeout: 30000 });
});
