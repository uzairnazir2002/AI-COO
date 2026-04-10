import { expect, test } from "./fixtures/auth";

test.describe("workforce leave", () => {
  test("leave page loads with tabs", async ({ page, authenticatedPage }) => {
    await authenticatedPage;
    await page.goto("/app/workforce/leave");
    await expect(page.getByRole("heading", { name: "Leave", exact: true })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Request" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Types" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Approvals" })).toBeVisible();
    // One of these primary states (avoid chaining .or() with two visible matches — strict mode).
    await expect(
      page
        .getByRole("heading", { name: "Select an organization to manage leave." })
        .or(page.getByRole("heading", { name: "Create a leave type first" }))
        .or(page.getByRole("button", { name: "Submit request" }))
        .or(page.getByRole("heading", { name: "Leave failed to load" })),
    ).toBeVisible();
  });
});
