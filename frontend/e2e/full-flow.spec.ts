import path from "node:path";

import { expect, test } from "./fixtures/auth";

test("full app flow: auth fixture -> dashboard -> transactions -> reports", async ({ page, authSession, authenticatedPage }) => {
  await authenticatedPage;
  await expect(page.locator("h1", { hasText: "Executive dashboard" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cashflow" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Revenue vs Expense" })).toBeVisible();

  await page.goto("/app/transactions");
  await expect(page.locator("h1", { hasText: "Transactions" })).toBeVisible();

  await page.getByRole("button", { name: "Add transaction" }).first().click();
  const addDialog = page.getByRole("dialog");
  await addDialog.locator('input[placeholder="Amount"]').fill("1500.00");
  await addDialog.locator('input[placeholder="Category"]').fill("Sales");
  await addDialog.getByRole("button", { name: /^Add$/ }).click();
  await expect(page.getByText("Transaction added")).toBeVisible();

  const csvPath = path.resolve(process.cwd(), "..", "shared", "demo", "transactions_6months.csv");
  await page.getByRole("button", { name: "Import CSV" }).click();
  await page.getByTestId("csv-file-input").setInputFiles(csvPath);
  await page.getByTestId("csv-preview-button").click();
  await expect(page.getByText(/Rows:/)).toBeVisible();
  await page.getByTestId("csv-confirm-button").click();
  await expect(page.getByText(/CSV imported/)).toBeVisible();

  await page.goto("/app/dashboard");
  await expect(page.getByRole("heading", { name: "Cashflow" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Revenue vs Expense" })).toBeVisible();

  await page.goto("/app/forecast");
  await expect(page.locator("h1", { hasText: "Forecast" })).toBeVisible();
  await expect(page.getByText("Scenario projection")).toBeVisible();
  await expect(page.getByText("Projected runway delta")).toBeVisible();

  await page.goto("/app/reports");
  await expect(page.locator("h1", { hasText: "Reports" })).toBeVisible();
  await page.getByRole("button", { name: "Generate report" }).first().click();
  await page.getByRole("button", { name: /Generate \/ Regenerate/ }).click();
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

  if (!process.env.E2E_USER_EMAIL) {
    expect(authSession.email).toContain(authSession.namespace);
  } else {
    expect(authSession.email).toBe(process.env.E2E_USER_EMAIL);
  }
  expect(authSession.orgId).toBeTruthy();
});
