import { expect, test } from "./fixtures/auth";

test("reports workflow: generate and surface recent jobs", async ({ page, authenticatedPage }) => {
  test.setTimeout(240_000);
  await authenticatedPage;

  await page.goto("/app/reports", { waitUntil: "domcontentloaded" });
  await expect(page.locator("h1", { hasText: "Reports" })).toBeVisible();

  await page.getByRole("button", { name: "Generate report" }).first().click();
  await expect(page.getByRole("heading", { name: "Generate weekly report" })).toBeVisible();
  await page.getByRole("button", { name: /Generate \/ Regenerate/ }).click();

  await expect
    .poll(async () => {
      const requested = await page.getByText("Report generation requested").count();
      const reused = await page.getByText("Report already available").count();
      return requested + reused;
    })
    .toBeGreaterThan(0);

  const toggle = page.getByRole("button", { name: /Show generation details|Hide generation details/i });
  if (await toggle.count()) {
    await toggle.first().click();
  }
  await expect(page.getByRole("heading", { name: "Recent report jobs" })).toBeVisible();
});

