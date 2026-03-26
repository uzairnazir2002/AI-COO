import path from "node:path";

import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures/auth";

async function clickCsvAction(page: Page, testId: string) {
  const button = page.getByTestId(testId);
  await button.scrollIntoViewIfNeeded();
  await expect(button).toBeEnabled();
  await button.evaluate((el) => (el as HTMLButtonElement).click());
}

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
  await clickCsvAction(page, "csv-preview-button");
  await expect(page.getByText(/Rows:/)).toBeVisible();
  await clickCsvAction(page, "csv-confirm-button");
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

  await expect(page.getByRole("heading", { name: "Recent report jobs" })).toBeVisible();
  await expect(page.getByText("generate_weekly_report")).toBeVisible({ timeout: 30_000 });
  const downloadBtn = page.getByRole("button", { name: "Download" }).first();
  if ((await downloadBtn.count()) > 0) {
    const downloadResponsePromise = page.waitForResponse(
      (res) => res.url().includes("/api/v1/reports/") && res.url().includes("/download") && res.request().method() === "GET",
    );
    await downloadBtn.click();
    const downloadResponse = await downloadResponsePromise;
    expect(downloadResponse.ok(), await downloadResponse.text()).toBeTruthy();
  }

  const seededEmail = process.env.E2E_USER_EMAIL;
  const isSeededSession = Boolean(seededEmail && authSession.email === seededEmail);
  if (isSeededSession) {
    expect(authSession.email).toBe(seededEmail);
  } else {
    expect(authSession.email).toContain(authSession.namespace);
  }
  expect(authSession.orgId).toBeTruthy();
});
