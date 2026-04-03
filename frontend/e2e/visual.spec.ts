import type { Page } from "@playwright/test";

import { expect, test } from "./fixtures/auth";

const themes = ["light", "dark"] as const;

async function applyTheme(page: Page, theme: (typeof themes)[number]) {
  await page.addInitScript((nextTheme: "light" | "dark") => {
    localStorage.setItem("theme", nextTheme);
    document.documentElement.classList.toggle("dark", nextTheme === "dark");
  }, theme);
}

test.describe("visual regression", () => {
  test.skip(process.env.E2E_VISUAL !== "1", "Visual snapshots run only when E2E_VISUAL=1");

  for (const theme of themes) {
    test(`dashboard snapshot (${theme})`, async ({ page, authenticatedPage }) => {
      await applyTheme(page, theme);
      await authenticatedPage;
      await page.goto("/app/dashboard");
      await expect(page.getByRole("heading", { name: /Executive dashboard|Business health/i })).toBeVisible();
      await expect(page).toHaveScreenshot(`dashboard-${theme}.png`, {
        fullPage: true,
        animations: "disabled",
        caret: "hide",
        maxDiffPixelRatio: 0.03,
        mask: [page.locator(".recharts-wrapper"), page.locator("pre")],
      });
    });

    test(`transactions snapshot (${theme})`, async ({ page, authenticatedPage }) => {
      await applyTheme(page, theme);
      await authenticatedPage;
      await page.goto("/app/transactions");
      await expect(page.getByRole("heading", { name: /Transactions|Money/i })).toBeVisible();
      await expect(page).toHaveScreenshot(`transactions-${theme}.png`, {
        fullPage: true,
        animations: "disabled",
        caret: "hide",
        maxDiffPixelRatio: 0.03,
        mask: [page.locator(".h-\\[520px\\]"), page.locator("input[type='date']")],
      });
    });

    test(`reports snapshot (${theme})`, async ({ page, authenticatedPage }) => {
      await applyTheme(page, theme);
      await authenticatedPage;
      await page.goto("/app/reports");
      await expect(page.getByRole("heading", { name: "Reports" })).toBeVisible();
      await expect(page).toHaveScreenshot(`reports-${theme}.png`, {
        fullPage: true,
        animations: "disabled",
        caret: "hide",
        maxDiffPixelRatio: 0.03,
        mask: [page.locator("p.text-xs.text-muted-foreground")],
      });
    });
  }
});
