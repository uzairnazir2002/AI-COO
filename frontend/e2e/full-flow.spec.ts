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
  test.setTimeout(300_000);
  await authenticatedPage;
  await expect(page.locator("h1", { hasText: /Executive dashboard|Business health/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cashflow" })).toBeVisible();
  const revenueExpenseHeading = page.getByRole("heading", { name: "Revenue vs Expense" });
  if (await revenueExpenseHeading.count()) {
    await expect(revenueExpenseHeading).toBeVisible();
  }

  await page.goto("/app/transactions");
  await expect(page.locator("h1", { hasText: /Transactions|Money/i })).toBeVisible();
  await expect(page.getByTestId("saved-view-selector")).toBeVisible();
  await expect(page.getByTestId("column-visibility-menu")).toBeVisible();

  await page.getByRole("button", { name: "Add transaction" }).first().click();
  const addDialog = page.getByRole("dialog");
  await addDialog.locator('input[placeholder="Amount"]').fill("1500.00");
  await addDialog.locator('input[placeholder="Category"]').fill("Sales");
  await addDialog.getByRole("button", { name: /^Add$/ }).click();
  await expect(page.getByText("Transaction added")).toBeVisible();

  const csvPath = path.resolve(process.cwd(), "..", "shared", "demo", "transactions_6months.csv");
  await page.getByRole("button", { name: "Import CSV" }).click();
  await page.getByTestId("csv-file-input").setInputFiles(csvPath);
  await expect(page.getByTestId("csv-step-status")).toContainText(/Step (2|3) -/);
  await clickCsvAction(page, "csv-preview-button");
  await expect(page.getByText(/Rows:/)).toBeVisible();
  await clickCsvAction(page, "csv-confirm-button");
  await expect(page.getByText(/CSV imported/)).toBeVisible();
  await page.getByRole("cell", { name: "Sales" }).first().click();
  await expect(page.getByText("Related alerts")).toBeVisible();
  await expect(page.getByText("Audit snippet")).toBeVisible();

  await page.goto("/app/dashboard");
  await expect(page.getByRole("heading", { name: "Cashflow" })).toBeVisible();
  if (await revenueExpenseHeading.count()) {
    await expect(revenueExpenseHeading).toBeVisible();
  }

  await page.goto("/app/alerts");
  await expect(page.locator("h1", { hasText: "Alerts" })).toBeVisible();
  await expect
    .poll(async () => {
      const quiet = await page.getByText("No alerts in this view.").count();
      const triPane = await page.getByRole("heading", { name: "Alert feed" }).count();
      const grouped = await page.getByRole("heading", { name: "Needs attention" }).count();
      return quiet + triPane + grouped;
    })
    .toBeGreaterThan(0);

  const triPaneFeed = page.getByRole("heading", { name: "Alert feed" });
  if (await triPaneFeed.count()) {
    await expect(triPaneFeed).toBeVisible();
    await expect(page.getByRole("heading", { name: "Action panel" })).toBeVisible();
  } else if (await page.getByRole("heading", { name: "Needs attention" }).count()) {
    await expect(page.getByRole("heading", { name: "Needs attention" })).toBeVisible();
  } else {
    await expect(page.getByText("No alerts in this view.").first()).toBeVisible();
  }

  await page.goto("/app/forecast");
  await expect(page.locator("h1", { hasText: "Forecast" })).toBeVisible();
  await expect(page.getByText("Scenario projection")).toBeVisible();
  const runwayImpact = page.getByText(/Projected runway delta|Projected runway|Runway impact/i).first();
  await expect(runwayImpact).toBeVisible();

  await page.goto("/app/reports");
  await expect(page.locator("h1", { hasText: "Reports" })).toBeVisible();
  await page.getByRole("button", { name: "Generate report" }).first().click();
  await page.getByRole("button", { name: /Generate \/ Regenerate/ }).click();
  await expect(page.getByText("Report generation requested")).toBeVisible();

  const showGenerationDetails = page.getByRole("button", { name: /Show generation details|Hide generation details/i });
  if (await showGenerationDetails.count()) {
    await showGenerationDetails.first().click();
  }
  await expect(page.getByRole("heading", { name: "Recent report jobs" })).toBeVisible();
  await expect(page.getByTestId("schedule-report-card")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Report metadata & sharing|Metadata & sharing/i })).toBeVisible();
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
