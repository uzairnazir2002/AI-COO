import { expect, test } from "./fixtures/auth";

test("inventory flow: mutate stock, queue refresh, and surface persisted stockout alert", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  const sku = `SKU-RISK-${Date.now()}`;

  await page.goto("/app/inventory");
  await expect(page.getByRole("heading", { name: "Inventory", exact: true })).toBeVisible();

  await page.getByPlaceholder("SKU (e.g. SKU-1001)").fill(sku);
  await page.getByPlaceholder("Item name").fill("Risky item");
  await page.getByPlaceholder("Unit cost").first().fill("4");
  await page.getByPlaceholder("Reorder point (qty)").fill("10");
  await page.getByRole("button", { name: "Create item" }).click();
  await expect(page.getByText("Inventory item created")).toBeVisible();
  await page.getByText(sku).first().click();
  await expect(page.getByRole("heading", { name: "Inventory detail" })).toBeVisible();
  await expect(page.getByText("Related alert context")).toBeVisible();
  await page.getByRole("button", { name: "Close" }).first().click();

  await page.getByRole("tab", { name: "Stock Events", exact: true }).click();
  await page.getByLabel("Stock event item").selectOption({ label: `${sku} - Risky item` });
  await page.getByLabel("Stock event type").selectOption("OUTBOUND");
  await page.getByPlaceholder("Quantity").first().fill("30");
  await page.getByRole("button", { name: "Record event" }).click();
  await expect(page.getByText("Stock event recorded")).toBeVisible();

  await page.getByRole("button", { name: "Open notifications" }).click();
  await expect(page.getByRole("heading", { name: "Notification Center" })).toBeVisible();
  await expect(page.getByText("Alert refresh queued", { exact: true }).first()).toBeVisible();

  await page.goto("/app/activity");
  await expect(page.getByRole("heading", { name: "Activity", exact: true })).toBeVisible({ timeout: 60_000 });
  await page.goto("/app/admin-console");
  await expect(page.getByRole("heading", { name: "Admin Console", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Queue analytics recompute" }).click();
  await expect(page.getByText("Analytics recompute queued")).toBeVisible();
  await expect(page.getByText("recalc_alerts")).toBeVisible({ timeout: 30_000 });

  await page.goto("/app/alerts");
  await expect(page.getByRole("heading", { name: "Alerts", exact: true })).toBeVisible();
  await expect(page.getByText(`Inventory stockout risk: ${sku}`)).toBeVisible({ timeout: 60_000 });
});
