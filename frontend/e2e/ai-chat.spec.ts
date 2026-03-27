import { expect, test } from "./fixtures/auth";

test("AI chat flow: create session, send message, and show grounded/fallback indicator", async ({ page, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/assistant");

  await expect(page.getByRole("heading", { name: "AI Chat", exact: true })).toBeVisible();

  await page.getByTestId("ai-chat-new-session").click();
  await expect(page.getByText("New chat started")).toBeVisible();

  await page.getByTestId("ai-chat-composer").fill("How is our cash position and immediate risk?");
  await page.getByTestId("ai-chat-send").click();

  await expect(page.getByTestId("ai-chat-user-message").last()).toContainText("How is our cash position and immediate risk?", {
    timeout: 30_000,
  });

  const assistantMessage = page.getByTestId("ai-chat-assistant-message").last();
  await expect(assistantMessage).toBeVisible({ timeout: 90_000 });
  await expect(assistantMessage).toContainText(/Grounded|Fallback/i);
});
