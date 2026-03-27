import { expect, test } from "./fixtures/auth";

test("transaction mutation emits alert refresh queue signal and yields persisted budget-threshold alert", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  const category = `Ops-${Date.now()}`;

  await page.goto("/app/budgets");
  await page.getByPlaceholder("Category (e.g. Ops)").fill(category);
  await page.getByPlaceholder("Planned amount").fill("100");
  await page.getByRole("button", { name: "Save budget" }).click();
  await expect(page.getByText("Budget saved")).toBeVisible();

  await page.goto("/app/transactions");
  await page.getByRole("button", { name: "Add transaction" }).first().click();
  const addDialog = page.getByRole("dialog");
  await addDialog.locator('input[placeholder="Amount"]').fill("170");
  await addDialog.locator('input[placeholder="Category"]').fill(category);
  await addDialog.getByRole("button", { name: /^Add$/ }).click();
  await expect(page.getByText("Transaction added")).toBeVisible();

  await page.getByRole("button", { name: "Open notifications" }).click();
  await expect(page.getByRole("heading", { name: "Notification Center" })).toBeVisible();
  await expect(page.getByText("Alert refresh queued", { exact: true })).toBeVisible();

  await page.goto("/app/activity");
  await expect(page.getByRole("heading", { name: "Activity" })).toBeVisible();
  await expect(page.getByText("recalc_alerts")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Queue analytics recompute" }).click();
  await expect(page.getByText("Analytics recompute queued")).toBeVisible();

  await page.goto("/app/alerts");
  await expect(page.getByRole("heading", { name: "Alerts", exact: true })).toBeVisible();
  await expect(page.getByText(`Budget threshold exceeded in ${category}`)).toBeVisible({ timeout: 60_000 });
});
