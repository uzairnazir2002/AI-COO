import { expect, test } from "./fixtures/auth";

test("imports workflow: upload → map → preview → commit → import history updates", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/transactions", { waitUntil: "domcontentloaded" });

  // Open import wizard
  await page.getByRole("button", { name: /Import CSV/i }).click();
  await expect(page.getByText(/CSV import wizard/i)).toBeVisible({ timeout: 30_000 });

  const csv = [
    "Date,Amount,Type,Category,Vendor,Notes",
    "2026-04-08,12.34,EXPENSE,Office,e2e-import,stationery",
    "2026-04-09,99.00,REVENUE,Sales,e2e-import,invoice-123",
  ].join("\n");

  await page.getByTestId("csv-file-input").setInputFiles({
    name: "e2e-import.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv, "utf-8"),
  });

  // Required mappings should auto-detect from headers; preview should now be enabled.
  await page.getByTestId("csv-preview-button").click();
  await expect(page.getByText(/Rows:\s*2/i)).toBeVisible({ timeout: 30_000 });

  // Confirm import (commit)
  await page.getByTestId("csv-confirm-button").click();
  await expect(page.getByText(/CSV imported/i)).toBeVisible({ timeout: 30_000 });

  // Import history should reflect a new entry (right rail or imports tab)
  await page.getByRole("tab", { name: "Imports" }).click();
  await expect(page.getByText(/Import center/i)).toBeVisible();
  await expect(page.getByText(/Latest imports/i)).toBeVisible();
});

