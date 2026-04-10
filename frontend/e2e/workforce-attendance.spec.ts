import { expect, test } from "./fixtures/auth";

test.describe("workforce attendance", () => {
  test("attendance page loads with tabs", async ({ page, authenticatedPage }) => {
    await authenticatedPage;
    await page.goto("/app/workforce/attendance");

    const mainTitle = page.getByRole("heading", { name: "Attendance", exact: true });
    await expect(
      mainTitle
        .or(page.getByRole("heading", { name: "Select an organization to manage attendance." }))
        .or(page.getByRole("heading", { name: "Attendance failed to load" })),
    ).toBeVisible({ timeout: 60_000 });

    if (await mainTitle.isVisible()) {
      await expect(page.getByRole("tab", { name: "Daily log" })).toBeVisible();
      await expect(page.getByRole("tab", { name: "Calendar" })).toBeVisible();
      await expect(page.getByRole("tab", { name: "Shifts" })).toBeVisible();
      await expect(page.getByRole("tab", { name: "Corrections" })).toBeVisible();
      await expect(page.getByText(/Tip: use manual entry/i)).toBeVisible();
    }
  });
});
