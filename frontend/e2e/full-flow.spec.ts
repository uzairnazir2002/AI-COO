import path from "node:path";

import { expect, test } from "./fixtures/auth";

test("full app flow: auth fixture -> dashboard -> transactions -> reports", async ({ page, authSession, authenticatedPage }) => {
  await authenticatedPage;

  await page.goto("/app/transactions");
  await expect(page.locator("h1", { hasText: "Transactions" })).toBeVisible();

  await page.locator('input[placeholder="Amount"]').first().fill("1500.00");
  await page.locator('input[placeholder="Category"]').first().fill("Sales");
  await page.getByRole("button", { name: "Add" }).click();
  await expect(page.getByText("Transaction added")).toBeVisible();

  const csvPath = path.resolve(process.cwd(), "..", "shared", "demo", "transactions_6months.csv");
  await page.locator('input[type="file"]').setInputFiles(csvPath);
  await page.getByRole("button", { name: "Preview Import" }).click();
  await expect(page.getByText(/Rows:/)).toBeVisible();

  await page.getByRole("button", { name: "Confirm Import" }).click();
  await expect(page.getByText(/CSV imported/)).toBeVisible();

  await page.goto("/app/reports");
  await expect(page.locator("h1", { hasText: "Reports" })).toBeVisible();
  await page.getByRole("button", { name: "Generate / Regenerate" }).click();
  await expect(page.getByText("Report generation requested")).toBeVisible();

  await page.waitForTimeout(2000);
  const downloadBtn = page.getByRole("button", { name: "Download" }).first();
  await expect(downloadBtn).toBeVisible({ timeout: 30_000 });

  const downloadResponsePromise = page.waitForResponse(
    (res) => res.url().includes("/api/v1/reports/") && res.url().includes("/download") && res.request().method() === "GET",
  );
  await downloadBtn.click();
  const downloadResponse = await downloadResponsePromise;
  expect(downloadResponse.ok(), await downloadResponse.text()).toBeTruthy();

  expect(authSession.email).toContain(authSession.namespace);
  expect(authSession.orgId).toBeTruthy();
});
