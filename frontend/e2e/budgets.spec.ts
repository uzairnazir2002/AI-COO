import { expect, test } from "./fixtures/auth";

test("budgets flow: create and version update", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/budgets");

  await expect(page.locator("h1", { hasText: "Budgets" })).toBeVisible();

  const category = `Ops-${Date.now()}`;
  await page.getByPlaceholder("Category (e.g. Ops)").fill(category);
  await page.getByPlaceholder("Planned amount").fill("1200");
  await page.getByRole("button", { name: "Save budget" }).click();
  await expect(page.getByText("Budget saved")).toBeVisible();

  await expect(page.getByRole("cell", { name: category }).first()).toBeVisible();
  const budgetRow = page.locator("tr", { hasText: category }).first();
  await budgetRow.getByRole("button", { name: "New version" }).click();
  await budgetRow.getByPlaceholder("Amount").fill("1400");
  await budgetRow.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Budget version updated")).toBeVisible();
});
