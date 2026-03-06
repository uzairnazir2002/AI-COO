import { expect, test as base, type Page } from "@playwright/test";

type AuthSession = {
  namespace: string;
  email: string;
  password: string;
  accessToken?: string;
  refreshToken?: string;
  orgId: string;
  authMode: "bearer" | "cookie";
};

type Fixtures = {
  authSession: AuthSession;
  authenticatedPage: void;
};

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";
const authMode = (process.env.E2E_AUTH_MODE || "bearer") as "bearer" | "cookie";
const seededEmail = process.env.E2E_USER_EMAIL;
const seededPassword = process.env.E2E_USER_PASSWORD;
const seededOrgId = process.env.E2E_ORG_ID;

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function validateSeededAuthEnv() {
  const configured = [seededEmail, seededPassword].filter(Boolean).length;
  if (configured !== 0 && configured !== 2) {
    throw new Error("E2E_USER_EMAIL and E2E_USER_PASSWORD must be provided together when using seeded confirmed auth.");
  }
}

async function setSelectedOrgState(page: Page, orgId: string) {
  await page.addInitScript((id: string) => {
    localStorage.setItem("ai-coo-app-store", JSON.stringify({ state: { selectedOrgId: id }, version: 0 }));
    document.cookie = `ai_coo_selected_org=${id}; path=/; max-age=31536000; SameSite=Lax`;
  }, orgId);
}

export const test = base.extend<Fixtures>({
  authSession: async ({ page }, use, testInfo) => {
    validateSeededAuthEnv();
    const namespace = `w${testInfo.workerIndex}-r${testInfo.repeatEachIndex}-${Date.now()}`;
    const email = seededEmail || `e2e_${namespace}_${Math.random().toString(16).slice(2, 8)}@example.com`;
    const password = seededPassword || "Password123!";

    if (!seededEmail || !seededPassword) {
      const reg = await page.request.post(`${apiBase}/auth/register`, {
        data: { email, password },
      });
      if (![200, 409].includes(reg.status())) {
        throw new Error(`register failed: ${reg.status()} ${await reg.text()}`);
      }
    }

    if (seededEmail) {
      // The backend currently derives refresh tokens from second-level timestamps.
      // Stagger seeded-user logins to avoid unique refresh-token-session collisions across workers.
      await delay(testInfo.workerIndex * 1200);
    }

    let login = await page.request.post(`${apiBase}/auth/login`, {
      data: { email, password },
    });
    if (!login.ok() && login.status() >= 500 && seededEmail) {
      await delay(1250);
      login = await page.request.post(`${apiBase}/auth/login`, {
        data: { email, password },
      });
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
    const me = (await meRes.json()) as { orgs: Array<{ org_id: string }> };

    let orgId = seededOrgId || me.orgs[0]?.org_id;
    if (!orgId) {
      const createOrg = await page.request.post(`${apiBase}/organizations`, {
        data: { name: `E2E Org ${namespace}` },
        headers: authMode === "bearer" ? { Authorization: `Bearer ${accessToken}` } : undefined,
      });
      expect(createOrg.ok(), `create org failed: ${await createOrg.text()}`).toBeTruthy();
      const created = (await createOrg.json()) as { org_id: string };
      orgId = created.org_id;
    }

    await setSelectedOrgState(page, orgId);

    await use({
      namespace,
      email,
      password,
      accessToken,
      refreshToken,
      orgId,
      authMode,
    });
  },

  authenticatedPage: async ({ page, authSession }, use) => {
    await page.goto("/app/dashboard");
    await page.waitForURL(/\/(app\/(dashboard|orgs)|auth\/login)/, { timeout: 30_000 });
    if (page.url().includes("/auth/login")) {
      throw new Error("authentication bootstrap failed: redirected to /auth/login");
    }
    if (page.url().includes("/app/orgs")) {
      await page.getByPlaceholder("Acme LLC").fill(`E2E Org ${authSession.namespace}`);
      await page.getByRole("button", { name: "Create" }).click();
      await page.waitForURL(/\/app\/dashboard/, { timeout: 30_000 });
    }
    await expect(page).toHaveURL(/\/app\/dashboard/);

    await page.addInitScript((orgId: string) => {
      localStorage.setItem("ai-coo-app-store", JSON.stringify({ state: { selectedOrgId: orgId }, version: 0 }));
      document.cookie = `ai_coo_selected_org=${orgId}; path=/; max-age=31536000; SameSite=Lax`;
    }, authSession.orgId);

    await use();
  },
});

export { expect };
