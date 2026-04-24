import fs from "node:fs";
import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

function loadEnvFile(filePath: string) {
  if (!fs.existsSync(filePath)) return;
  const content = fs.readFileSync(filePath, "utf8");
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    const value = line.slice(eq + 1).trim().replace(/^['"]|['"]$/g, "");
    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

const frontendDir = __dirname;
loadEnvFile(path.join(frontendDir, ".env.e2e.local"));
loadEnvFile(path.join(frontendDir, ".env.local"));
loadEnvFile(path.join(frontendDir, "..", ".env"));

const e2eBaseURL = process.env.E2E_BASE_URL || "http://localhost:3001";
const e2eUrl = new URL(e2eBaseURL);
const e2eHost = e2eUrl.hostname;
const e2ePort = Number(e2eUrl.port || (e2eUrl.protocol === "https:" ? "443" : "80"));
const e2eWebServerMode = process.env.E2E_WEB_SERVER_MODE || "start";
/** When unset/false, Playwright starts `next build && next start` on `E2E_BASE_URL` (default :3001). If `E2E_USE_EXTERNAL_BASE_URL=1`, tests hit whatever is already running — it must match the current frontend build or UI tests will see stale bundles. */
const useExternalBaseUrl = process.env.E2E_USE_EXTERNAL_BASE_URL === "1";
/** Avoid stale Next bundles during Playwright runs (can mask UI changes in e2e). */
const cleanNextCache = `node -e "try{require('fs').rmSync('.next',{recursive:true,force:true});}catch(e){}"`;
/**
 * Next.js builds can race with `.next` deletion on some Windows setups (observed missing pages-manifest.json).
 * Allow opting out when diagnosing flaky e2e webServer startup.
 */
const shouldCleanNextCache = process.env.E2E_CLEAN_NEXT_CACHE !== "0";
const webServerCommand =
  e2eWebServerMode === "dev"
    ? `npm run dev -- --hostname ${e2eHost} --port ${e2ePort}`
    : `${shouldCleanNextCache ? `${cleanNextCache} && ` : ""}npm run build && npm run start -- --hostname ${e2eHost} --port ${e2ePort}`;

export default defineConfig({
  globalSetup: path.join(frontendDir, "e2e", "global-setup.ts"),
  testDir: "./e2e",
  snapshotPathTemplate: "{testDir}/__screenshots__/{testFilePath}/{arg}{ext}",
  timeout: 180_000,
  expect: { timeout: 15_000 },
  workers: Number(process.env.E2E_WORKERS || "1"),
  fullyParallel: false,
  retries: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: e2eBaseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: useExternalBaseUrl
    ? undefined
    : {
        command: webServerCommand,
        cwd: frontendDir,
        url: e2eBaseURL,
        timeout: 900_000,
        reuseExistingServer: false,
        stdout: "pipe",
        stderr: "pipe",
      },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
