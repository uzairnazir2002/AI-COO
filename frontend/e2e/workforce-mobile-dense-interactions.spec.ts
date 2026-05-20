import { expect, test } from "./fixtures/auth";

test.describe("workforce mobile dense interaction coverage", () => {
  test("attendance and payroll controls stay usable on mobile width", async ({ page, authenticatedPage }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await authenticatedPage;

    await page.goto("/app/workforce/attendance");
    await expect(page.getByRole("heading", { name: "Attendance", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Add record" })).toBeVisible();

    const attendanceMainOverflow = await page.locator("main").evaluate((el) => el.scrollWidth - el.clientWidth);
    expect(attendanceMainOverflow).toBeLessThanOrEqual(24);

    await page.getByRole("tab", { name: "Shifts" }).click();
    await expect(page.getByText("Shifts and assignments power lateness detection.")).toBeVisible();
    await page.getByRole("button", { name: "New shift" }).click();
    const shiftDialog = page.getByRole("dialog");
    await expect(page.getByRole("heading", { name: "Create shift" })).toBeVisible();
    await expect(shiftDialog.getByPlaceholder("e.g. General")).toBeVisible();
    await expect(shiftDialog.locator("input[type='time']").first()).toBeVisible();
    await expect(shiftDialog.locator("input[type='time']").nth(1)).toBeVisible();
    await page.keyboard.press("Escape");

    await page.goto("/app/workforce/payroll");
    await expect(page.getByRole("heading", { name: "Payroll", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "New period" }).click();
    await expect(page.getByRole("heading", { name: "Create payroll period" })).toBeVisible();
    await expect(page.getByLabel("Start date")).toBeVisible();
    await expect(page.getByLabel("End date")).toBeVisible();

    const payrollDialogOverflow = await page.locator("[role='dialog']").evaluate((el) => el.scrollWidth - el.clientWidth);
    expect(payrollDialogOverflow).toBeLessThanOrEqual(24);
  });
});
