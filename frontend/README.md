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
- Core flows covered:
  - login/bootstrap -> create org -> add transaction -> dashboard/reports flow
  - CSV import happy path
  - report generate + download
  - forecast overrides
  - RBAC smoke for hidden mutation controls in viewer-style UI
- Shared fixture: [e2e/fixtures/auth.ts](/C:/Project/AI%20COO/ai-coo/frontend/e2e/fixtures/auth.ts)
- Default E2E env:
  - `E2E_BASE_URL=http://localhost:3000`
  - `E2E_API_URL=http://localhost:8000/api/v1`
  - `E2E_AUTH_MODE=bearer|cookie`
  - `E2E_CSRF_COOKIE_NAME`
  - `E2E_CSRF_HEADER_NAME`
- Seeded confirmed user standard:
  - Prefer a long-lived confirmed test account when the backend requires `/api/v1/auth/confirm` after registration.
  - Set `E2E_USER_EMAIL` and `E2E_USER_PASSWORD` together.
  - Optionally set `E2E_ORG_ID` to pin tests to a specific organization.
  - If no seeded credentials are provided, the fixture falls back to runtime registration and login.
  - If only one of `E2E_USER_EMAIL` or `E2E_USER_PASSWORD` is set, the fixture fails fast with a configuration error.

## Architecture rules
- Page components stay thin and rely on feature hooks for data.
- API calls go through [src/lib/api/client.ts](/C:/Project/AI%20COO/ai-coo/frontend/src/lib/api/client.ts).
- `/app/*` routes are protected by session bootstrap in [src/app/app/layout.tsx](/C:/Project/AI%20COO/ai-coo/frontend/src/app/app/layout.tsx).
- Org context persists in Zustand plus `ai_coo_selected_org` cookie.
- Dashboard and reports keep server-prefetch support for faster first paint.

## Graceful UI fallbacks
- Reports generation shows a frontend "generating" state because the current endpoint does not expose detailed job progress there.
- Forecast empty states explain when insufficient historical data prevents useful output.
- Settings and billing panels remain read-only when backend capability or role access is unavailable.
- Notification stream auto-falls back to polling after sustained SSE failures and resumes live mode when stream connectivity returns.
