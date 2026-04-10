import { expect, test } from "./fixtures/auth";

test("stripe reconciliation shows friendly invalid date range error", async ({ page, authenticatedPage }) => {
  await authenticatedPage;

  await page.goto("/app/settings", { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "Integrations" }).click();

  const card = page.getByTestId("stripe-reconciliation-card");
  await expect(card).toBeVisible({ timeout: 60_000 });

  const fromInput = card.locator('input[type="date"]').nth(0);
  const toInput = card.locator('input[type="date"]').nth(1);

  // Force invalid range: from > to
  await fromInput.fill("2026-04-10");
  await toInput.fill("2026-04-01");

  await card.getByRole("button", { name: "Refresh" }).click();

  await expect
    .poll(async () => {
      const text = await card.textContent();
      return text || "";
    })
    .toContain("Invalid date range. Ensure “From” is earlier than “To”, then refresh.");
});

