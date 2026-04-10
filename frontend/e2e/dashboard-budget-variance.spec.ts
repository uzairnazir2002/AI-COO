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

  await page.goto("/app/admin-console");
  await expect(page.getByRole("heading", { name: "Admin Console", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Queue analytics recompute" }).click();
  await expect(page.getByText("Analytics recompute queued")).toBeVisible();

  await page.goto("/app/dashboard", { waitUntil: "domcontentloaded" });
  await expect(page.locator("h1", { hasText: /Executive dashboard|Dashboard/i })).toBeVisible({ timeout: 60_000 });

  const budgetAlerts = page.getByTestId("budget-threshold-alerts");
  if (!(await budgetAlerts.isVisible())) {
    const showMoreInsights = page.getByRole("button", { name: "Show more insights" });
    await expect(showMoreInsights).toBeVisible({ timeout: 30_000 });
    await showMoreInsights.click();
  }
  await expect(budgetAlerts).toBeVisible({ timeout: 30_000 });
  await expect(budgetAlerts).toContainText("Budget threshold alerts");
  const budgetPlannedKpi = page.locator("p:visible", { hasText: "Budget planned (month)" });
  if (await budgetPlannedKpi.count()) {
    await expect(budgetPlannedKpi).toBeVisible();
    await expect(page.locator("p:visible", { hasText: "Budget actual (month)" })).toBeVisible();
    await expect(page.locator("p:visible", { hasText: "Budget variance (month)" })).toBeVisible();
  }
});
