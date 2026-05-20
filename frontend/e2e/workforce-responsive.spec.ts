import { expect, test } from "./fixtures/auth";

const viewports = [
  { name: "mobile", size: { width: 390, height: 844 } },
  { name: "tablet", size: { width: 768, height: 1024 } },
  { name: "desktop", size: { width: 1280, height: 800 } },
  { name: "large-desktop", size: { width: 1536, height: 960 } },
];

const routes = [
  "/app/workforce",
  "/app/workforce/employees",
  "/app/workforce/attendance",
  "/app/workforce/leave",
  "/app/workforce/payroll",
  "/app/workforce/communications",
  "/app/workforce/hr",
];

test.describe("workforce responsive gate", () => {
  for (const vp of viewports) {
    test(`${vp.name}: routes render and remain usable`, async ({ page, authenticatedPage }) => {
      await page.setViewportSize(vp.size);
      await authenticatedPage;

      for (const route of routes) {
        await page.goto(route);
        await expect(page).toHaveURL(new RegExp(route.replace("/", "\\/")));
        await expect(page.locator("main")).toBeVisible();
      }

      await page.goto("/app/workforce/payroll");
      await expect(page.getByRole("heading", { name: "Payroll", exact: true })).toBeVisible();
      await expect(page.getByText("Payroll period", { exact: true })).toBeVisible();

      await page.goto("/app/workforce/attendance");
      await expect(page.getByRole("heading", { name: "Attendance", exact: true })).toBeVisible();

      await page.goto("/app/workforce/communications");
      await expect(page.getByRole("heading", { name: "Communications", exact: true })).toBeVisible();
    });
  }
});
