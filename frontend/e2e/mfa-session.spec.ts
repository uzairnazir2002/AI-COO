import crypto from "node:crypto";

import { expect, test } from "./fixtures/auth";

const apiBase = process.env.E2E_API_URL || "http://localhost:8000/api/v1";
const apiRetryAttempts = Math.max(1, Number(process.env.E2E_API_RETRY_ATTEMPTS || 3));
const apiRetryDelayMs = Math.max(200, Number(process.env.E2E_API_RETRY_DELAY_MS || 700));
const apiRequestTimeoutMs = Math.max(10_000, Number(process.env.E2E_API_REQUEST_TIMEOUT_MS || 45_000));

function totpCode(secret: string, time = Date.now()): string {
  const normalized = secret.toUpperCase();
  const key = decodeBase32(normalized);
  const counter = Math.floor(time / 1000 / 30);
  const counterBuffer = Buffer.alloc(8);
  counterBuffer.writeBigUInt64BE(BigInt(counter));
  const hmac = crypto.createHmac("sha1", key).update(counterBuffer).digest();
  const offset = hmac[hmac.length - 1] & 0x0f;
  const code = ((hmac.readUInt32BE(offset) & 0x7fffffff) % 1_000_000).toString();
  return code.padStart(6, "0");
}

function decodeBase32(input: string): Buffer {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const ch of input.replace(/=+$/g, "")) {
    const idx = alphabet.indexOf(ch);
    if (idx < 0) continue;
    bits += idx.toString(2).padStart(5, "0");
  }
  const bytes: number[] = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) {
    bytes.push(parseInt(bits.slice(i, i + 8), 2));
  }
  return Buffer.from(bytes);
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function requestWithRetry<T>(run: () => Promise<T>) {
  let lastError: unknown = null;
  for (let attempt = 1; attempt <= apiRetryAttempts; attempt += 1) {
    try {
      return await run();
    } catch (error) {
      lastError = error;
      if (attempt < apiRetryAttempts) {
        await delay(apiRetryDelayMs * attempt);
      }
    }
  }
  throw lastError instanceof Error ? lastError : new Error("request failed after retries");
}

test("mfa and session API smoke", async ({ page, authSession, authenticatedPage }) => {
  await authenticatedPage;
  await page.goto("/app/settings");
  await page.getByRole("tab", { name: "Security", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Multi-factor authentication" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Session management" })).toBeVisible();

  const headers = authSession.authMode === "bearer" && authSession.accessToken
    ? { Authorization: `Bearer ${authSession.accessToken}` }
    : undefined;

  const setup = await page.request.post(`${apiBase}/auth/mfa/setup`, {
    headers,
    data: { password: authSession.password },
  });
  expect(setup.ok(), await setup.text()).toBeTruthy();
  const setupBody = (await setup.json()) as { secret: string };
  const code = totpCode(setupBody.secret);

  const enable = await page.request.post(`${apiBase}/auth/mfa/enable`, {
    headers,
    data: { code },
  });
  expect(enable.ok(), await enable.text()).toBeTruthy();
  const enableBody = (await enable.json()) as { recovery_codes: string[] };
  expect(enableBody.recovery_codes.length).toBeGreaterThan(0);

  const sessions = await requestWithRetry(() =>
    page.request.get(
      `${apiBase}/auth/sessions${authSession.authMode === "bearer" && authSession.refreshToken ? `?refresh_token=${encodeURIComponent(authSession.refreshToken)}` : ""}`,
      { headers, timeout: apiRequestTimeoutMs },
    ),
  );
  expect(sessions.ok(), await sessions.text()).toBeTruthy();

  const revokeOthers = await requestWithRetry(() =>
    page.request.post(`${apiBase}/auth/sessions/revoke-others`, {
      headers,
      timeout: apiRequestTimeoutMs,
      data: authSession.authMode === "bearer" ? { refresh_token: authSession.refreshToken } : {},
    }),
  );
  expect(revokeOthers.ok(), await revokeOthers.text()).toBeTruthy();
});
