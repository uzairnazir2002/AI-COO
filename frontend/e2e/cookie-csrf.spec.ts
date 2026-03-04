import { expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";
const csrfCookieName = process.env.E2E_CSRF_COOKIE_NAME || "ai_coo_csrf_token";
const csrfHeaderName = process.env.E2E_CSRF_HEADER_NAME || "X-CSRF-Token";

test.describe("cookie-mode csrf", () => {
  test.skip((process.env.E2E_AUTH_MODE || "bearer") !== "cookie", "Cookie CSRF spec runs only in cookie mode");

  test("blocks mutating request without CSRF and allows with CSRF", async ({ page, authenticatedPage, authSession }) => {
    await authenticatedPage;

    const noCsrfStatus = await page.evaluate(async ({ apiBase, namespace }) => {
      const res = await fetch(`${apiBase}/organizations`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: `NoCSRF-${namespace}` }),
      });
      return res.status;
    }, { apiBase, namespace: authSession.namespace });

    expect(noCsrfStatus).toBe(403);

    const withCsrfStatus = await page.evaluate(async ({ apiBase, csrfCookieName, csrfHeaderName, namespace }) => {
      const cookie = document.cookie
        .split("; ")
        .find((entry) => entry.startsWith(`${csrfCookieName}=`));
      const token = cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers[csrfHeaderName] = token;
      const res = await fetch(`${apiBase}/organizations`, {
        method: "POST",
        credentials: "include",
        headers,
        body: JSON.stringify({ name: `WithCSRF-${namespace}` }),
      });
      return res.status;
    }, { apiBase, csrfCookieName, csrfHeaderName, namespace: authSession.namespace });

    expect(withCsrfStatus).toBe(200);
  });
});
