import path from "node:path";

import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures/auth";

async function chooseSelectOptionByTestId(page: Page, testId: string, option: string) {
  await page.getByTestId(testId).click();
  await page.getByRole("option", { name: option }).click();
}

test("transactions csv mapping required-field guard disables import actions", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/transactions");
  await expect(page.locator("h1", { hasText: "Transactions" })).toBeVisible();

  await page.getByRole("button", { name: "Import CSV" }).click();
  const csvPath = path.resolve(process.cwd(), "..", "shared", "demo", "transactions_6months.csv");
  await page.getByTestId("csv-file-input").setInputFiles(csvPath);
  await expect(page.getByText("Column mapping")).toBeVisible();

  await chooseSelectOptionByTestId(page, "csv-map-date", "Not mapped");
  await expect(page.getByText(/Missing required mappings: Date/)).toBeVisible();
  await expect(page.getByTestId("csv-preview-button")).toBeDisabled();
  await expect(page.getByTestId("csv-confirm-button")).toBeDisabled();
});

test("transactions bulk remap success path updates category and shows toast", async ({ page, authenticatedPage, authSession }) => {
  await authenticatedPage;
  await page.goto("/app/transactions");
  await expect(page.locator("h1", { hasText: "Transactions" })).toBeVisible();

  const fromCategory = `From-${authSession.namespace}`;
  const toCategory = `To-${authSession.namespace}`;

  await page.getByRole("button", { name: "Add transaction" }).first().click();
  let addDialog = page.getByRole("dialog");
  await addDialog.locator('input[placeholder="Amount"]').fill("101.00");
  await addDialog.locator('input[placeholder="Category"]').fill(fromCategory);
  await addDialog.getByRole("button", { name: /^Add$/ }).click();
  await expect(page.getByText("Transaction added")).toBeVisible();

  await page.getByRole("button", { name: "Add transaction" }).first().click();
  addDialog = page.getByRole("dialog");
  await addDialog.locator('input[placeholder="Amount"]').fill("102.00");
  await addDialog.locator('input[placeholder="Category"]').fill(fromCategory);
  await addDialog.getByRole("button", { name: /^Add$/ }).click();
  await expect(page.getByText("Transaction added").first()).toBeVisible();

  await page.getByTestId("bulk-remap-from-category").fill(fromCategory);
  await page.getByTestId("bulk-remap-to-category").fill(toCategory);
  const remapResponsePromise = page.waitForResponse(
    (res) => res.url().includes("/api/v1/transactions/bulk/remap-category") && res.request().method() === "POST",
  );
  await page.getByTestId("bulk-remap-submit").click();
  const remapResponse = await remapResponsePromise;
  const remapBody = await remapResponse.text();
  expect(remapResponse.status(), remapBody).toBe(200);

  await expect(page.getByText("Bulk remap applied")).toBeVisible();
  await expect(page.getByText(/Updated \d+ rows/)).toBeVisible();
});

test("forecast inline override supports dirty state, save and reset", async ({ page, authenticatedPage }) => {
  await authenticatedPage;

  const csvPath = path.resolve(process.cwd(), "..", "shared", "demo", "transactions_6months.csv");
  await page.goto("/app/transactions");
  await page.getByRole("button", { name: "Import CSV" }).click();
  await page.getByTestId("csv-file-input").setInputFiles(csvPath);
  await page.getByTestId("csv-confirm-button").click();
  await expect(page.getByText(/CSV imported/)).toBeVisible();

  await page.goto("/app/forecast");
  await expect(page.locator("h1", { hasText: "Forecast" })).toBeVisible();

  const revenueInput = page.locator('[data-testid^="forecast-override-revenue-"]').first();
  await expect(revenueInput).toBeVisible();
  const revenueTestId = await revenueInput.getAttribute("data-testid");
  expect(revenueTestId).toBeTruthy();
  const month = revenueTestId!.replace("forecast-override-revenue-", "");

  await revenueInput.fill("12345");
  await expect(page.getByTestId("forecast-dirty-count")).toContainText("Dirty rows: 1");

  await page.getByTestId(`forecast-reset-${month}`).click();
  await expect(page.getByTestId("forecast-dirty-count")).toContainText("Dirty rows: 0");

  const expenseInput = page.getByTestId(`forecast-override-expense-${month}`);
  await expenseInput.fill("54321");
  await expect(page.getByTestId("forecast-dirty-count")).toContainText("Dirty rows: 1");

  await page.getByTestId(`forecast-save-${month}`).click();
  await expect(page.getByText(`Override saved for ${month}`)).toBeVisible();
  await expect(page.getByTestId("forecast-dirty-count")).toContainText("Dirty rows: 0");
});

test("rbac smoke: viewer-style UI does not expose add transaction action", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.route("**/api/v1/auth/me", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.orgs = json.orgs.map((org: { org_id: string; name: string }) => ({ ...org, role: "VIEWER" }));
    await route.fulfill({ response, json });
  });
  await page.goto("/app/transactions");
  await expect(page.getByText("Viewer role detected")).toBeVisible();
  await expect(page.getByRole("button", { name: "Add transaction" })).toHaveCount(0);

  await page.goto("/app/settings");
  await expect(page.getByText("Only owners can view and invite members.")).toBeVisible();
  await expect(page.getByPlaceholder("member@example.com")).toHaveCount(0);
});
