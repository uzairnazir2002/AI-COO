# AI COO Frontend

Next.js App Router + TypeScript frontend for AI COO.

## Stack
- Next.js App Router
- TailwindCSS with tokenized light/dark executive theme
- shadcn-style UI primitives
- TanStack Query for server state
- TanStack Table + react-virtual for transactions
- Recharts for charts
- Zod for critical API response validation
- Zustand for persisted app state
- Framer Motion for transitions and toasts
- Shared chart system with consistent tooltip and formatting

## Routes
- `/auth/login`
- `/auth/register`
- `/app/orgs`
- `/app/dashboard`
- `/app/transactions`
- `/app/forecast`
- `/app/alerts`
- `/app/reports`
- `/app/settings`

## Environment variables
- `NEXT_PUBLIC_API_URL` or `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_INTERNAL_API_URL` for server-side prefetch when frontend and backend use different internal network addresses
- `NEXT_PUBLIC_AUTH_MODE=bearer|cookie`
- `NEXT_PUBLIC_CSRF_COOKIE_NAME` default `ai_coo_csrf_token`
- `NEXT_PUBLIC_CSRF_HEADER_NAME` default `X-CSRF-Token`
- `NEXT_PUBLIC_CSV_MAX_BYTES` optional CSV upload cap override
- `NEXT_PUBLIC_SSE_RECONNECT_DELAY_MS` default `5000`
- `NEXT_PUBLIC_SSE_FAILURE_THRESHOLD` default `3`
- `NEXT_PUBLIC_SSE_FALLBACK_POLL_INTERVAL_MS` default `15000`
- `NEXT_PUBLIC_PLAID_LINK_SCRIPT_URL` optional override (default Plaid CDN script)

## Auth mode notes
- `bearer`
  - Tokens are stored in localStorage and sent as `Authorization: Bearer ...`
  - Refresh uses `/api/v1/auth/refresh` with the stored refresh token
- `cookie`
  - Session is carried by HttpOnly cookies
  - Mutating requests automatically add the CSRF header using the double-submit token cookie
  - Server-side prefetch works best when `NEXT_INTERNAL_API_URL` can reach the backend from the Next.js server

## Chart and UX notes
- Dashboard:
  - cashflow chart supports day/week/month granularity
  - KPI cards include mini trend sparklines
- Transactions:
  - virtualized table remains primary source of truth
  - category donut is clearly labeled as approximate: "Based on current filtered results."
- Forecast:
  - confidence interval band + scenario lines
  - override saves are marked in-chart for quick visual verification
- Alerts:
  - impact bars normalized across current list
  - detail drawer renders metadata safely without backend-specific assumptions

## Development
```bash
npm install
npm run dev
```

## Quality commands
```bash
npm run lint
npm run build
npm run analyze
npm run check
npm run e2e
npm run e2e:full
npm run e2e:smoke
npm run e2e:smoke:ci
npm run e2e:sse
npm run e2e:integrations
npm run e2e:cookie
npm run e2e:visual
npm run e2e:visual:update
```

## Performance notes
- Transactions list remains virtualized (`@tanstack/react-virtual`) for large datasets.
- Chart datasets are memoized and downsampled before rendering for smoother interactions.
- Route-level code splitting is preserved by App Router page boundaries.
- Bundle inspection is available via `npm run analyze`.

## E2E notes

### What runs today
- Full product flow, CSV import, reports, forecast, RBAC smoke, SSE/cookie/Stripe/Plaid where configured.
- **Responsive:** `e2e/responsive-mobile.spec.ts` (narrow viewport + slide-out nav) and `e2e/responsive-smoke.spec.ts` (tablet).
- **Onboarding:** `e2e/onboarding-workspace.spec.ts` — authenticated `/app/onboarding` shell.
- **Auth confirm UI:** `e2e/auth-confirm-ui.spec.ts` — `/auth/confirm` form and invalid-token error (needs API).

### Shared auth fixture
- [`e2e/fixtures/auth.ts`](e2e/fixtures/auth.ts) — login/register, CSRF when the CSRF cookie is present, optional seeded user.
- [`e2e/global-setup.ts`](e2e/global-setup.ts) — compares `E2E_AUTH_MODE` with `GET /api/v1/health` → `auth_cookie_mode` and **fails fast** on mismatch. Set `E2E_SKIP_AUTH_PREFLIGHT=1` only if you intentionally bypass this (e.g. odd local setups).

### Base URL and managed server (important)
- [`playwright.config.ts`](playwright.config.ts) defaults **`E2E_BASE_URL`** to **`http://localhost:3001`** and starts **`next build && next start`** on that host/port unless you opt out.
- Repo or Docker docs often use **`:3000`**. If `E2E_BASE_URL` points at the wrong port, tests hit the wrong app or fail to connect.
- **`E2E_USE_EXTERNAL_BASE_URL=1`** skips Playwright’s web server and uses whatever is already listening. Only enable it when that server is built from the **same commit** as the tests; otherwise you may run against **stale bundles** and get confusing UI failures.

### Recommended local command (managed frontend)
```bash
cd frontend
# Windows PowerShell example — align with playwright.config default:
$env:E2E_BASE_URL = "http://localhost:3001"
Remove-Item Env:E2E_USE_EXTERNAL_BASE_URL -ErrorAction SilentlyContinue
$env:E2E_API_URL = "http://localhost:8000/api/v1"
npx playwright test
```

### Other E2E env
- `E2E_API_URL` — default `http://localhost:8000/api/v1`
- `E2E_AUTH_MODE=bearer|cookie`
- **Backend `AUTH_COOKIE_MODE` must match how you authenticate in tests.** `npm run e2e:smoke` with `E2E_AUTH_MODE=bearer` expects JSON access tokens from `/auth/login` (CI uses `.env.example`, i.e. `AUTH_COOKIE_MODE=false`). If the API runs with `AUTH_COOKIE_MODE=true`, use `E2E_AUTH_MODE=cookie` and `NEXT_PUBLIC_AUTH_MODE=cookie` on the frontend under test, or run smoke against a bearer-token API like CI.
- `E2E_CSRF_COOKIE_NAME` / `E2E_CSRF_HEADER_NAME` (cookie mode)
- **`E2E_FORCE_VIEWPORT=W×H`** — set by `responsive-mobile.spec.ts` via `authenticatedPage` so navigation runs at mobile width before layout mounts.
- **`E2E_SKIP_AUTH_PREFLIGHT=1`** — skip global-setup cookie/bearer alignment check.
- **`e2e:smoke:ci`** — CI-parity env vars + smoke list (stack must already be listening on `:3000` / `:8000`).
- **`e2e:sse`** — runs `sse-fallback.spec.ts` with `E2E_SSE=1`.
- **`e2e:integrations`** — Plaid + Stripe optional specs (each file self-skips without sandbox secrets / `E2E_*` flags).
- Optional Plaid sandbox: `E2E_PLAID_SANDBOX=1`, `E2E_PLAID_PUBLIC_TOKEN=…`
- Seeded confirmed user: set **`E2E_USER_EMAIL`** and **`E2E_USER_PASSWORD`** together; optional **`E2E_ORG_ID`**. Otherwise the fixture registers a disposable user (and may call dev confirmation helpers when the API allows).

## Architecture rules
- Page components stay thin and rely on feature hooks for data.
- API calls go through [`src/lib/api/client.ts`](src/lib/api/client.ts).
- `/app/*` routes are protected by session bootstrap in [`src/app/app/layout.tsx`](src/app/app/layout.tsx).
- Org context persists in Zustand plus `ai_coo_selected_org` cookie.
- Dashboard and reports keep server-prefetch support for faster first paint.

## Graceful UI fallbacks
- Reports generation shows a frontend "generating" state because the current endpoint does not expose detailed job progress there.
- Plaid connection UI supports link-token generation and public-token exchange; full Plaid Link popup wiring can be layered on top of this backend contract.
- Forecast empty states explain when insufficient historical data prevents useful output.
- Settings and billing panels remain read-only when backend capability or role access is unavailable.
- Notification stream auto-falls back to polling after sustained SSE failures and resumes live mode when stream connectivity returns.
