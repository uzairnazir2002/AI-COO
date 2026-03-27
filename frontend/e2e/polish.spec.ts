import path from "node:path";

import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";

async function chooseSelectOptionByTestId(page: Page, testId: string, option: string) {
  await page.getByTestId(testId).click();
  await page.getByRole("option", { name: option }).click();
}

async function clickCsvAction(page: Page, testId: string) {
  const button = page.getByTestId(testId);
  await button.scrollIntoViewIfNeeded();
  await expect(button).toBeEnabled();
  await button.evaluate((el) => (el as HTMLButtonElement).click());
}

test("transactions csv mapping required-field guard disables import actions", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/transactions");
  await expect(page.locator("h1", { hasText: "Transactions" })).toBeVisible();

  await page.getByRole("button", { name: "Import CSV" }).click();
  const csvPath = path.resolve(process.cwd(), "..", "shared", "demo", "transactions_6months.csv");
  await page.getByTestId("csv-file-input").setInputFiles(csvPath);
  await expect(page.getByText("Column mapping")).toBeVisible();
  await expect(page.getByTestId("csv-action-footer")).toBeVisible();

  await chooseSelectOptionByTestId(page, "csv-map-date", "Not mapped");
  await expect(page.getByText(/Missing required mappings: Date/)).toBeVisible();
  await expect(page.getByTestId("csv-preview-button")).toBeDisabled();
  await expect(page.getByTestId("csv-confirm-button")).toBeDisabled();
});

test("guided onboarding rail appears for a fresh organization", async ({ page, authenticatedPage, authSession }) => {
  await authenticatedPage;
  test.skip(authSession.authMode !== "bearer", "Onboarding rail bootstrap helper currently uses bearer-mode org creation.");

  const createOrg = await page.request.post(`${apiBase}/organizations`, {
    data: { name: `Onboarding ${authSession.namespace}` },
    headers: { Authorization: `Bearer ${authSession.accessToken}` },
  });
  expect(createOrg.ok(), await createOrg.text()).toBeTruthy();
  const created = (await createOrg.json()) as { org_id: string };

  await page.evaluate((orgId: string) => {
    localStorage.setItem(
      "ai-coo-app-store",
      JSON.stringify({
        state: { selectedOrgId: orgId },
        version: 0,
      }),
    );
    document.cookie = `ai_coo_selected_org=${orgId}; path=/; max-age=31536000; SameSite=Lax`;
  }, created.org_id);

  await page.goto("/app/dashboard");
  await expect(page.getByTestId("onboarding-progress-rail")).toBeVisible();
  await expect(page.getByTestId("onboarding-progress-next")).toBeVisible();
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
  await expect(addDialog).toBeHidden({ timeout: 10000 });

  await page.getByRole("button", { name: "Add transaction" }).first().click();
  addDialog = page.getByRole("dialog");
  await addDialog.locator('input[placeholder="Amount"]').fill("102.00");
  await addDialog.locator('input[placeholder="Category"]').fill(fromCategory);
  await addDialog.getByRole("button", { name: /^Add$/ }).click();
  await expect(page.getByText("Transaction added").first()).toBeVisible();
  await expect(addDialog).toBeHidden({ timeout: 10000 });

  const fromInput = page.getByTestId("bulk-remap-from-category");
  const toInput = page.getByTestId("bulk-remap-to-category");
  const submit = page.getByTestId("bulk-remap-submit");

  await fromInput.fill(fromCategory);
  await toInput.fill(toCategory);
  await expect(fromInput).toHaveValue(fromCategory);
  await expect(toInput).toHaveValue(toCategory);
  await expect(submit).toBeEnabled({ timeout: 15000 });

  const remapResponsePromise = page.waitForResponse(
    (res) => res.url().includes("/api/v1/transactions/bulk/remap-category") && res.request().method() === "POST",
  );
  await submit.click();
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
  await clickCsvAction(page, "csv-confirm-button");
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
