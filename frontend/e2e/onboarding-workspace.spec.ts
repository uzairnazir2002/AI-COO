import { expect, test } from "./fixtures/auth";

test("onboarding workspace loads after auth", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/onboarding");
  await expect(page.getByRole("heading", { name: "Guided onboarding" })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("tab", { name: "Guided path" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Checklist" })).toBeVisible();
});
