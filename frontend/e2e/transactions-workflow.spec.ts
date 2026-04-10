import { expect, test } from "./fixtures/auth";

test("transactions workflow: create → edit → bulk delete", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/transactions", { waitUntil: "domcontentloaded" });

  const vendor = `e2e-vendor-${Date.now()}`;

  // Create (scope to dialog — page can expose multiple "Add transaction" triggers)
  await page.getByRole("button", { name: /Add transaction/i }).first().click();
  const createDialog = page.getByRole("dialog");
  await createDialog.getByPlaceholder("Amount").fill("12.34");
  await createDialog.getByPlaceholder("Category").fill("e2e-workflow");
  await createDialog.getByPlaceholder("Vendor").fill(vendor);
  await createDialog.getByRole("button", { name: /^Add$/ }).click();
  await expect(page.getByText(/Transaction added/i)).toBeVisible({ timeout: 30_000 });

  // Filter down to the created row
  await page.getByPlaceholder("Search vendor/notes").fill(vendor);
  await expect(page.getByText(/1 records|1 record/i)).toBeVisible({ timeout: 30_000 });

  // Open detail drawer by clicking the row (click the vendor cell text)
  await page.getByText(vendor, { exact: true }).first().click();
  await expect(page.getByText(/Transaction detail/i)).toBeVisible({ timeout: 30_000 });

  // Edit via quick edit
  await page.getByRole("button", { name: /Quick edit/i }).click();
  await page.locator("input[name='amount']").fill("23.45");
  await page.getByRole("button", { name: /^Save$/ }).click();
  await expect(page.getByText(/^Updated$/)).toBeVisible({ timeout: 30_000 });

  await page.getByTestId("detail-drawer").getByRole("button", { name: "Close" }).first().click();
  await expect(page.getByTestId("detail-drawer")).toBeHidden({ timeout: 15_000 });

  await page.getByText(vendor, { exact: true }).first().scrollIntoViewIfNeeded();

  // Bulk delete the single filtered row (header checkbox is nth(0); first data row is nth(1))
  const rowCheckbox = page.getByRole("checkbox").nth(1);
  await rowCheckbox.scrollIntoViewIfNeeded();
  await rowCheckbox.check();

  const bulkBar = page.getByTestId("transactions-bulk-action-bar");
  await expect(bulkBar).toBeVisible({ timeout: 15_000 });
  await bulkBar.getByRole("button", { name: /Delete selected/i }).evaluate((el) => (el as HTMLButtonElement).click());
  await expect(page.getByText(/Selected transactions deleted/i)).toBeVisible({ timeout: 30_000 });
});

