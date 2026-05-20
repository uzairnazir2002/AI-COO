import { expect, test as base, type Page } from "@playwright/test";

type AuthSession = {
  namespace: string;
  email: string;
  password: string;
  accessToken?: string;
  refreshToken?: string;
  orgId: string;
  orgs: SessionOrg[];
  authMode: "bearer" | "cookie";
};

type SessionOrg = {
  org_id: string;
  role: "OWNER" | "EDITOR" | "MANAGER" | "VIEWER";
  name: string;
};

type Fixtures = {
  authSession: AuthSession;
  authenticatedPage: void;
};

// Prefer IPv4 loopback by default on Windows (some setups bind the API to 127.0.0.1 but not ::1).
const apiBase = process.env.E2E_API_URL || "http://127.0.0.1:8000/api/v1";
const authMode = (process.env.E2E_AUTH_MODE || "bearer") as "bearer" | "cookie";
const csrfCookieName = process.env.E2E_CSRF_COOKIE_NAME || "ai_coo_csrf_token";
const csrfHeaderName = process.env.E2E_CSRF_HEADER_NAME || "X-CSRF-Token";
const seededEmail = process.env.E2E_USER_EMAIL;
const seededPassword = process.env.E2E_USER_PASSWORD;
const seededOrgId = process.env.E2E_ORG_ID;
const useSeededIdentity = process.env.E2E_USE_SEEDED === "1";
const loginRetryLimit = Math.max(1, Number(process.env.E2E_LOGIN_RETRY_LIMIT || 5));
const loginBackoffBaseMs = Math.max(100, Number(process.env.E2E_LOGIN_BACKOFF_BASE_MS || 400));
const loginBackoffMaxMs = Math.max(loginBackoffBaseMs, Number(process.env.E2E_LOGIN_BACKOFF_MAX_MS || 3_500));
const apiOrigin = (() => {
  try {
    return new URL(apiBase).origin;
  } catch {
    return undefined;
  }
})();

const runNonce = `${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
let uniqueIdentityCounter = 0;
let seededIdentityDisabledForRun = false;

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function confirmAccountIfNeeded(page: Page, email: string) {
  const tokenRes = await page.request.get(`${apiBase}/auth/dev/confirmation-token`, {
    params: { email },
  });
  if (!tokenRes.ok()) {
    return false;
  }
  const tokenJson = (await tokenRes.json()) as { token?: string | null; found?: boolean };
  if (!tokenJson.found || !tokenJson.token) {
    return false;
  }
  const confirmRes = await postWithCookieCsrf(page, `${apiBase}/auth/confirm`, {
    data: { token: tokenJson.token },
  });
  return confirmRes.ok();
}

function validateSeededAuthEnv() {
  const configured = [seededEmail, seededPassword].filter(Boolean).length;
  if (configured !== 0 && configured !== 2) {
    throw new Error("E2E_USER_EMAIL and E2E_USER_PASSWORD must be provided together when using seeded confirmed auth.");
  }
}

function nextUniqueIdentity(workerIndex: number) {
  uniqueIdentityCounter += 1;
  const namespace = `w${workerIndex}-${runNonce}-${uniqueIdentityCounter}`;
  return {
    namespace,
    email: `e2e_${namespace}@example.com`,
    password: "Password123!",
  };
}

async function ensureRegistered(page: Page, email: string, password: string, errorPrefix = "register failed") {
  let reg = await postWithCookieCsrf(page, `${apiBase}/auth/register`, {
    data: { email, password },
  });
  if (reg.status() === 429) {
    await delay(loginBackoffMaxMs);
    reg = await postWithCookieCsrf(page, `${apiBase}/auth/register`, {
      data: { email, password },
    });
  }
  if (![200, 409].includes(reg.status())) {
    throw new Error(`${errorPrefix}: ${reg.status()} ${await reg.text()}`);
  }
}

async function readCookieFromContext(page: Page, name: string): Promise<string | undefined> {
  const cookies = apiOrigin ? await page.context().cookies([apiOrigin]) : await page.context().cookies();
  return cookies.find((cookie) => cookie.name === name)?.value;
}

async function withCookieCsrfHeaders(
  page: Page,
  headers?: Record<string, string>,
): Promise<Record<string, string> | undefined> {
  /**
   * When the API runs with AUTH_COOKIE_MODE, register/login set session cookies even if E2E uses
   * bearer tokens from the JSON body. Mutating requests that carry those cookies require a matching
   * CSRF header — so always forward the CSRF cookie when present, not only for E2E_AUTH_MODE=cookie.
   */
  const csrfToken = await readCookieFromContext(page, csrfCookieName);
  if (!csrfToken) return headers;
  return {
    ...(headers || {}),
    [csrfHeaderName]: csrfToken,
  };
}

async function postWithCookieCsrf(
  page: Page,
  url: string,
  options: { data?: unknown; headers?: Record<string, string> },
) {
  const headers = await withCookieCsrfHeaders(page, options.headers);
  return page.request.post(url, {
    data: options.data,
    headers,
  });
}

/** Minimal session shape for E2E calls that must work in bearer or cookie auth mode. */
export type E2eAuthSessionSlice = {
  authMode: "bearer" | "cookie";
  accessToken?: string;
  orgId?: string;
};

export async function e2eAuthenticatedPost(page: Page, url: string, data: unknown, session: E2eAuthSessionSlice) {
  const orgHeaders: Record<string, string> = {};
  if (session.orgId) orgHeaders["X-Org-Id"] = session.orgId;
  if (session.authMode === "bearer") {
    const token = session.accessToken;
    if (!token) throw new Error("E2E bearer mode requires accessToken on auth session");
    return page.request.post(url, {
      data,
      headers: { Authorization: `Bearer ${token}`, ...orgHeaders },
    });
  }
  return postWithCookieCsrf(page, url, { data, headers: orgHeaders });
}

export async function e2eAuthenticatedGet(page: Page, url: string, session: E2eAuthSessionSlice) {
  const orgHeaders: Record<string, string> = {};
  if (session.orgId) orgHeaders["X-Org-Id"] = session.orgId;
  if (session.authMode === "bearer") {
    const token = session.accessToken;
    if (!token) throw new Error("E2E bearer mode requires accessToken on auth session");
    return page.request.get(url, {
      headers: { Authorization: `Bearer ${token}`, ...orgHeaders },
    });
  }
  return page.request.get(url, { headers: orgHeaders });
}

async function loginWithBackoff(page: Page, email: string, password: string) {
  let last = await postWithCookieCsrf(page, `${apiBase}/auth/login`, { data: { email, password } });
  if (last.ok()) {
    return last;
  }

  for (let attempt = 2; attempt <= loginRetryLimit; attempt += 1) {
    const retryable = last.status() === 429 || last.status() >= 500;
    if (!retryable) {
      return last;
    }
    const delayMs = Math.min(loginBackoffMaxMs, loginBackoffBaseMs * 2 ** (attempt - 2));
    await delay(delayMs);
    last = await postWithCookieCsrf(page, `${apiBase}/auth/login`, { data: { email, password } });
    if (last.ok()) {
      return last;
    }
  }
  return last;
}

async function setSelectedOrgState(page: Page, orgId: string, orgs: SessionOrg[]) {
  await page.addInitScript(
    ({ id, availableOrgs }: { id: string; availableOrgs: SessionOrg[] }) => {
      localStorage.setItem(
        "ai-coo-app-store",
        JSON.stringify({
          state: {
            selectedOrgId: id,
            orgs: availableOrgs,
          },
          version: 0,
        }),
      );
    document.cookie = `ai_coo_selected_org=${id}; path=/; max-age=31536000; SameSite=Lax`;
    },
    { id: orgId, availableOrgs: orgs },
  );
}

async function seedBrowserSessionState(page: Page, session: AuthSession) {
  await page.goto("/auth/login", { waitUntil: "domcontentloaded" });
  await page.evaluate(
    (payload: {
      orgId: string;
      orgs: SessionOrg[];
      authMode: "bearer" | "cookie";
      accessToken?: string;
      refreshToken?: string;
    }) => {
      localStorage.setItem(
        "ai-coo-app-store",
        JSON.stringify({
          state: {
            selectedOrgId: payload.orgId,
            orgs: payload.orgs,
          },
          version: 0,
        }),
      );
      if (payload.authMode === "bearer" && payload.accessToken) {
        localStorage.setItem("ai_coo_access_token", payload.accessToken);
      }
      if (payload.authMode === "bearer" && payload.refreshToken) {
        localStorage.setItem("ai_coo_refresh_token", payload.refreshToken);
      }
      document.cookie = `ai_coo_selected_org=${payload.orgId}; path=/; max-age=31536000; SameSite=Lax`;
    },
    {
      orgId: session.orgId,
      orgs: session.orgs,
      authMode: session.authMode,
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
    },
  );
}

async function loginThroughUi(page: Page, email: string, password: string) {
  await page.goto("/auth/login", { waitUntil: "domcontentloaded" });
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /Sign in/i }).click();
  await page.waitForURL(/\/(app\/(dashboard|orgs)|auth\/login)/, { timeout: 30_000 });
}

export const test = base.extend<Fixtures>({
  authSession: async ({ page }, use, testInfo) => {
    validateSeededAuthEnv();
    const uniqueIdentity = nextUniqueIdentity(testInfo.workerIndex);
    let namespace = uniqueIdentity.namespace;
    let email = uniqueIdentity.email;
    let password = uniqueIdentity.password;
    let usingSeeded = Boolean(useSeededIdentity && seededEmail && seededPassword && !seededIdentityDisabledForRun);

    if (usingSeeded) {
      email = seededEmail as string;
      password = seededPassword as string;
      namespace = `seeded-${uniqueIdentity.namespace}`;
      await delay(testInfo.workerIndex * 900);
    } else {
      await ensureRegistered(page, email, password);
    }

    let login = await loginWithBackoff(page, email, password);
    if (!login.ok() && [400, 401].includes(login.status())) {
      const confirmed = await confirmAccountIfNeeded(page, email);
      if (confirmed) {
        login = await loginWithBackoff(page, email, password);
      }
    }

    if (!login.ok() && usingSeeded) {
      seededIdentityDisabledForRun = true;
      usingSeeded = false;
      email = uniqueIdentity.email;
      password = uniqueIdentity.password;
      namespace = uniqueIdentity.namespace;
      await ensureRegistered(page, email, password, "seed fallback register failed");
      await confirmAccountIfNeeded(page, email);
      login = await loginWithBackoff(page, email, password);
    }

    if (!login.ok() && login.status() === 429 && !usingSeeded) {
      await delay(loginBackoffMaxMs);
      login = await loginWithBackoff(page, email, password);
    }

    expect(login.ok(), `login failed: ${await login.text()}`).toBeTruthy();
    const loginJson = (await login.json()) as { access_token?: string | null; refresh_token?: string | null };

    let accessToken: string | undefined;
    let refreshToken: string | undefined;
    if (authMode === "bearer") {
      accessToken = loginJson.access_token || undefined;
      refreshToken = loginJson.refresh_token || undefined;
      if (!accessToken) {
        throw new Error("bearer mode expected access token in login response");
      }
      await page.addInitScript(
        ({ accessToken, refreshToken }: { accessToken: string; refreshToken?: string }) => {
          localStorage.setItem("ai_coo_access_token", accessToken);
          if (refreshToken) {
            localStorage.setItem("ai_coo_refresh_token", refreshToken);
          }
        },
        { accessToken, refreshToken },
      );
    }

    const meRes = await page.request.get(`${apiBase}/auth/me`, {
      headers: authMode === "bearer" ? { Authorization: `Bearer ${accessToken}` } : undefined,
    });
    expect(meRes.ok(), `auth/me failed: ${await meRes.text()}`).toBeTruthy();
    const me = (await meRes.json()) as {
      orgs: Array<{ org_id: string; role: "OWNER" | "EDITOR" | "VIEWER"; name: string }>;
    };
    const knownOrgs: SessionOrg[] = [...me.orgs];
    const seededOrgIsAccessible = Boolean(seededOrgId && knownOrgs.some((org) => org.org_id === seededOrgId));

    let orgId = seededOrgIsAccessible ? seededOrgId : knownOrgs[0]?.org_id;
    if (!orgId) {
      const createOrg = await postWithCookieCsrf(page, `${apiBase}/organizations`, {
        data: { name: `E2E Org ${namespace}` },
        headers: authMode === "bearer" ? { Authorization: `Bearer ${accessToken}` } : undefined,
      });
      expect(createOrg.ok(), `create org failed: ${await createOrg.text()}`).toBeTruthy();
      const created = (await createOrg.json()) as { org_id: string; name?: string };
      orgId = created.org_id;
      knownOrgs.push({
        org_id: created.org_id,
        role: "OWNER",
        name: created.name || `E2E Org ${namespace}`,
      });
    }

    if (!knownOrgs.some((org) => org.org_id === orgId)) {
      knownOrgs.push({
        org_id: orgId,
        role: "OWNER",
        name: `E2E Org ${namespace}`,
      });
    }
    await setSelectedOrgState(page, orgId, knownOrgs);

    await use({
      namespace,
      email,
      password,
      accessToken,
      refreshToken,
      orgId,
      orgs: knownOrgs,
      authMode,
    });
  },

  authenticatedPage: async ({ page, authSession }, use) => {
    const forcedViewport = process.env.E2E_FORCE_VIEWPORT;
    if (forcedViewport) {
      const parts = forcedViewport.split("x").map((p) => Number.parseInt(p, 10));
      if (parts.length === 2 && Number.isFinite(parts[0]) && Number.isFinite(parts[1])) {
        await page.setViewportSize({ width: parts[0], height: parts[1] });
      }
    }

    let lastLoginError: string | null = null;
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      await seedBrowserSessionState(page, authSession);
      await page.goto("/app/dashboard");
      await page.waitForURL(/\/(app\/(dashboard|orgs)|auth\/login)/, { timeout: 30_000 });

      if (page.url().includes("/auth/login")) {
        const relogin = await loginWithBackoff(page, authSession.email, authSession.password);
        if (!relogin.ok()) {
          lastLoginError = `relogin attempt ${attempt} failed: ${relogin.status()} ${await relogin.text()}`;
          continue;
        }
        if (authSession.authMode === "bearer") {
          const reloginJson = (await relogin.json()) as { access_token?: string | null; refresh_token?: string | null };
          authSession.accessToken = reloginJson.access_token || undefined;
          authSession.refreshToken = reloginJson.refresh_token || undefined;
          if (!authSession.accessToken) {
            lastLoginError = `relogin attempt ${attempt} did not return access token`;
            continue;
          }
        }

        await seedBrowserSessionState(page, authSession);
        await page.goto("/app/dashboard");
        await page.waitForURL(/\/(app\/(dashboard|orgs)|auth\/login)/, { timeout: 30_000 });

        if (page.url().includes("/auth/login")) {
          await loginThroughUi(page, authSession.email, authSession.password);
          if (page.url().includes("/auth/login")) {
            const bodyText = (await page.locator("body").innerText()).slice(0, 220).replace(/\s+/g, " ").trim();
            lastLoginError = `attempt ${attempt} still redirected to /auth/login after API+UI bootstrap. Page snippet: ${bodyText}`;
            continue;
          }
        }
      }

      if (page.url().includes("/app/orgs")) {
        await page.getByPlaceholder("Acme LLC").fill(`E2E Org ${authSession.namespace}`);
        await page.getByRole("button", { name: "Create" }).click();
        await page.waitForURL(/\/app\/dashboard/, { timeout: 30_000 });
      }
      await expect(page).toHaveURL(/\/app\/dashboard/);
      await use();
      return;
    }
    throw new Error(lastLoginError || "authentication bootstrap failed after retries");
  },
});

export { expect };
