import { expect, test } from "./fixtures/auth";

test("dashboard shows budget variance KPIs and threshold alerts", async ({ page, authenticatedPage }) => {
  await authenticatedPage;

  await page.goto("/app/budgets");
  await page.getByPlaceholder("Category (e.g. Ops)").fill("Ops");
  await page.getByPlaceholder("Planned amount").fill("100");
  await page.getByRole("button", { name: "Save budget" }).click();
  await expect(page.getByText("Budget saved")).toBeVisible();

  await page.goto("/app/transactions");
  await page.getByRole("button", { name: "Add transaction" }).first().click();
  const addDialog = page.getByRole("dialog");
  await addDialog.locator('input[placeholder="Amount"]').fill("160");
  await addDialog.locator('input[placeholder="Category"]').fill("Ops");
  await addDialog.getByRole("button", { name: /^Add$/ }).click();
  await expect(page.getByText("Transaction added")).toBeVisible();

  await page.goto("/app/activity");
  await page.getByRole("button", { name: "Queue analytics recompute" }).click();
  await expect(page.getByText("Analytics recompute queued")).toBeVisible();

  await page.goto("/app/dashboard");
  await expect(page.getByText("Budget planned (month)")).toBeVisible();
  await expect(page.getByText("Budget actual (month)")).toBeVisible();
  await expect(page.getByText("Budget variance (month)")).toBeVisible();
  await expect(page.getByTestId("budget-threshold-alerts")).toContainText("Budget threshold alerts");
});
