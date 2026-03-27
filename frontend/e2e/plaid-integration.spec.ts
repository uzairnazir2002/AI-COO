import { test, expect } from "./fixtures/auth";

const livePlaid = process.env.E2E_PLAID_SANDBOX === "1";
const publicToken = process.env.E2E_PLAID_PUBLIC_TOKEN || "";

test.describe("Plaid integration flow", () => {
  test.skip(!livePlaid || !publicToken, "Set E2E_PLAID_SANDBOX=1 and E2E_PLAID_PUBLIC_TOKEN");

  test("connects bank via public token and enqueues sync", async ({ page, authenticatedPage }) => {
    void authenticatedPage;
    await page.goto("/app/settings");
    await expect(page.getByRole("heading", { name: "Bank integrations (Plaid)" })).toBeVisible();

    // In sandbox automation mode, use manual fallback exchange path directly
    // to avoid external Plaid iframe overlay interfering with in-app controls.
    await page.getByText("Advanced manual public token exchange").click();
    await page.getByPlaceholder("Plaid public_token").fill(publicToken);
    await page.getByRole("button", { name: "Exchange token manually" }).click();

    await expect(page.getByText("Bank connection added")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sync now" }).first()).toBeVisible();
    await page.getByRole("button", { name: "Sync now" }).first().click();
    await expect(page.getByText("Sync enqueued")).toBeVisible();
  });
});
