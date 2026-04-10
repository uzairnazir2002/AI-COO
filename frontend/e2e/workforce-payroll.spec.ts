import { expect, test } from "./fixtures/auth";

test.describe("workforce payroll", () => {
  test("payroll page loads with period picker", async ({ page, authenticatedPage }) => {
    await authenticatedPage;
    await page.goto("/app/workforce/payroll");
    await expect(page.getByRole("heading", { name: "Payroll", exact: true })).toBeVisible();
    await expect(page.getByText("Payroll period", { exact: true })).toBeVisible();
    await expect(
      page
        .getByRole("heading", { name: "Select a payroll period." })
        .or(page.getByRole("heading", { name: /Select an organization to manage payroll/i })),
    ).toBeVisible();
  });
});
