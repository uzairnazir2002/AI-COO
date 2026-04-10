import type { FullConfig } from "@playwright/test";

/**
 * Fail fast when Playwright auth transport disagrees with the API (avoids opaque CSRF / missing-token failures).
 */
async function globalSetup(_config: FullConfig) {
  if (process.env.E2E_SKIP_AUTH_PREFLIGHT === "1") {
    return;
  }

  const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";
  const authMode = (process.env.E2E_AUTH_MODE || "bearer").toLowerCase();

  let body: { auth_cookie_mode?: boolean };
  try {
    const res = await fetch(`${apiBase}/health`);
    if (!res.ok) {
      console.warn(`[e2e global-setup] GET ${apiBase}/health returned ${res.status}; skipping auth/cookie preflight.`);
      return;
    }
    body = (await res.json()) as { auth_cookie_mode?: boolean };
  } catch (err) {
    console.warn(`[e2e global-setup] health check failed (${String(err)}); skipping auth preflight.`);
    return;
  }

  if (typeof body.auth_cookie_mode !== "boolean") {
    console.warn("[e2e global-setup] health response missing auth_cookie_mode; skipping preflight (older API?).");
    return;
  }

  if (authMode === "bearer" && body.auth_cookie_mode) {
    throw new Error(
      `[e2e] E2E_AUTH_MODE=bearer but API reports auth_cookie_mode=true. ` +
        `Use AUTH_COOKIE_MODE=false (see .env.example / CI smoke) for bearer-driven Playwright, ` +
        `or run with E2E_AUTH_MODE=cookie and NEXT_PUBLIC_AUTH_MODE=cookie. ` +
        `Skip: E2E_SKIP_AUTH_PREFLIGHT=1.`,
    );
  }

  if (authMode === "cookie" && !body.auth_cookie_mode) {
    throw new Error(
      `[e2e] E2E_AUTH_MODE=cookie but API reports auth_cookie_mode=false. ` +
        `Enable AUTH_COOKIE_MODE=true for cookie/CSRF flows. Skip: E2E_SKIP_AUTH_PREFLIGHT=1.`,
    );
  }
}

export default globalSetup;
