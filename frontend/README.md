# AI COO Frontend

Next.js App Router + TypeScript frontend for AI COO SaaS.

## Stack
- Next.js App Router
- TailwindCSS + tokenized theme (light/dark)
- TanStack Query for server state
- TanStack Table + react-virtual for transaction table
- Recharts for charts
- Zod for critical API response validation
- Zustand for minimal global client state (`selectedOrgId`, `user`, org memberships)
- Framer Motion for subtle animations (toasts)

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

## Env
- `NEXT_PUBLIC_API_URL` (preferred) or `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_AUTH_MODE` = `bearer` or `cookie`
- `NEXT_PUBLIC_CSRF_COOKIE_NAME` (default `ai_coo_csrf_token`)
- `NEXT_PUBLIC_CSRF_HEADER_NAME` (default `X-CSRF-Token`)

## Development
```bash
npm install
npm run dev
```

## Quality checks
```bash
npm run lint
npm run build
npm run check
npm run e2e
npm run e2e:cookie
npm run e2e:visual
npm run e2e:visual:update
```

## E2E setup
- E2E tests live in `frontend/e2e`.
- Shared auth/session fixture: `frontend/e2e/fixtures/auth.ts`.
- Fixture uses a parallel-safe namespace (`workerIndex + repeatEachIndex + timestamp`) for user/org test data.
- Default E2E env:
  - `E2E_BASE_URL=http://localhost:3000`
  - `E2E_API_URL=http://localhost:8000/api/v1`
  - `E2E_AUTH_MODE=bearer|cookie`
  - `E2E_CSRF_COOKIE_NAME` and `E2E_CSRF_HEADER_NAME` (for cookie-mode CSRF spec)
- Visual snapshots:
  - Spec: `frontend/e2e/visual.spec.ts`
  - Baselines are split by theme (`light` + `dark`): `dashboard-light.png`, `dashboard-dark.png`, etc.
  - Dynamic regions (timestamps/table/chart volatility) are masked per page to reduce snapshot noise.
  - Baseline snapshots are created/updated via `npm run e2e:visual:update`

## Architecture rules
- Page components do not call fetch directly; they use feature hooks in `src/features/*`.
- API calls go through `src/lib/api/client.ts` (401 refresh single-flight + consistent error handling).
- `/app/*` routes are protected by session bootstrap in `src/app/app/layout.tsx`.
- RBAC UI gating is enforced using role helpers in `src/lib/auth/rbac.ts`.
- Dashboard and Reports use server-side TanStack Query prefetch + `HydrationBoundary` for faster first paint when cookie-auth context is available.

## Notes
- Settings page edits financial thresholds when available from backend. If settings endpoint is unavailable, UI falls back to read-only messaging.
- Report download supports signed URL responses (opens in new tab).
- Bulk category remap sends `org_id` in both query and body to satisfy backend RBAC dependency + payload validation.

## Current verification snapshot (March 5, 2026)
- `npm run lint`: pass
- `npm run build`: pass
- `npx playwright test --workers=1 --retries=0`: pass for non-visual bearer suite
- Skipped tests are expected unless explicitly enabled:
  - `cookie-csrf.spec.ts` requires `E2E_AUTH_MODE=cookie`
  - `visual.spec.ts` requires `E2E_VISUAL=1`
