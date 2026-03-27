# Frontend Current-State Handover (Deep Audit)

## 1) Audit Scope and Verification Snapshot

This document captures the current **implemented frontend state** so another AI/designer can safely redesign without breaking behavior.

Verification executed on latest local code:

- `pytest backend/app/tests/test_alert_assignment_api.py -q` -> **8 passed**
- `npx playwright test e2e/alert-refresh-queue.spec.ts --reporter=line` -> **1 passed**
- `npm run lint` -> **pass**
- `npm run build` -> **pass** (Next.js 15.5.12)

422 fix implemented in this pass:

- Backend alert endpoints now accept mixed legacy/new payload shapes for assign/acknowledge (query + body compatibility) to prevent 422 from strict body parsing mismatch.
- Files:
  - `backend/app/api/v1/alerts.py`
  - `backend/app/tests/test_alert_assignment_api.py`

## 2) Frontend Stack and Runtime Model

- Framework: Next.js App Router (`frontend/src/app/*`)
- UI: Tailwind + Radix primitives + custom components
- Data: TanStack Query
- Client state: Zustand (`frontend/src/store/appStore.ts`)
- Charts: Recharts + custom chart wrappers
- Motion: Framer Motion
- E2E: Playwright (`frontend/e2e/*`)

Runtime API/auth model:

- API base from `NEXT_PUBLIC_API_URL` or `NEXT_PUBLIC_API_BASE_URL`
- Auth supports both:
  - bearer token mode
  - cookie+CSRF mode
- API client centralizes:
  - token refresh
  - auth-expired event emission
  - network/CORS failure event emission
  - request id headers (`X-Request-ID`)

Primary files:

- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/api/endpoints.ts`
- `frontend/src/lib/auth/session.ts`
- `frontend/src/components/common/global-api-feedback.tsx`

## 3) Global App Skeleton and UX Frame

### 3.1 Layout tree

- Root providers in `frontend/src/app/layout.tsx`
- Query + theme + global feedback + toasts in `frontend/src/components/common/providers.tsx`
- Protected shell in `frontend/src/app/app/layout.tsx`
- Main shell component in `frontend/src/components/shell/app-shell.tsx`

### 3.2 Shell behavior

- Left sidebar nav (Dashboard, Activity, Transactions, Inventory, Budgets, Forecast, AI Chat, Alerts, Reports, Settings)
- Sticky top header with:
  - org selector
  - location selector
  - date range control
  - command palette
  - notifications center
  - logout
- Sidebar/main scroll separation is implemented:
  - sidebar pinned on desktop
  - main content scrolls in independent container

### 3.3 Theming/visual baseline

- Typography: IBM Plex Sans + Space Grotesk
- Light/dark CSS token system in `frontend/src/app/globals.css`
- Visual language: glass-panel cards, soft gradients, rounded corners

## 4) Route Inventory (Actual Implemented Frontend)

## 4.1 Public/auth routes

- `/` -> redirects to `/auth/login`
- `/auth/login` -> login form with MFA/recovery code support
- `/auth/register` -> registration or invite acceptance mode
- `/auth/confirm` -> token confirmation + resend flow
- Legacy aliases under `/(auth)` and top-level aliases redirect/forward to current auth routes

Core files:

- `frontend/src/features/auth/login-form.tsx`
- `frontend/src/features/auth/register-form.tsx`
- `frontend/src/app/(auth)/confirm/page.tsx`

## 4.2 Protected app routes

- `/app/dashboard` -> KPI + cashflow + variance + benchmark + alerts + AI summary
- `/app/activity` -> jobs/outbox/system status/SLO/dead-letter/security admin views
- `/app/transactions` -> table CRUD + filters + virtualization + CSV wizard + mapping profiles + import history + bulk remap
- `/app/inventory` -> item setup, stock events, PO creation, forecast risk table
- `/app/budgets` -> budget CRUD/versioning + variance lines
- `/app/forecast` -> scenarios/confidence bands/override editor
- `/app/assistant` -> AI chat sessions + message panel + grounded/fallback indicators
- `/app/alerts` -> alert stream, assign/unassign/acknowledge/dismiss + history panel
- `/app/reports` -> async report generation UX + job status + download/preview
- `/app/settings` -> org controls, financial settings, locations, owner policy, MFA, sessions, billing, Plaid, Stripe, members, compliance actions
- `/app/onboarding` -> guided readiness steps and progress
- `/app/orgs` -> org list + org creation

Top-level protected aliases also exist and wrap app pages via protected layout:

- `/dashboard`, `/transactions`, `/forecast`, `/reports`, `/settings`, `/activity`, `/budgets`, `/onboarding`

## 5) Feature-by-Feature Behavior Details

## 5.1 Auth/session

Implemented:

- Login with optional MFA code and recovery code
- Session bootstrap via `/auth/me`
- Automatic refresh token handling
- Global session-expired modal with return-to support
- Network/CORS warning toasts

Primary files:

- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/auth/session.ts`
- `frontend/src/components/common/global-api-feedback.tsx`

## 5.2 Dashboard

Implemented:

- Summary KPIs
- Cashflow and revenue/expense charts
- Budget variance KPI cards
- Cross-location benchmark section
- Alert cards + detail drawer
- AI executive summary panel with fallback badge

Primary files:

- `frontend/src/features/dashboard/dashboard-page-client.tsx`
- `frontend/src/features/dashboard/hooks.ts`

## 5.3 Transactions and CSV import

Implemented:

- Virtualized table and pagination
- Create/update/delete with optimistic updates
- Filtering (date/type/category/search)
- CSV import wizard with:
  - auto column detection
  - required-field guard
  - local duplicate preview signal
  - server preview/commit
  - persistent mapping profiles (save/update/delete/shared)
  - sticky action footer
- Import history + downloadable error blobs
- Bulk category remap
- Alert refresh metadata from response headers surfaced to users

Primary files:

- `frontend/src/app/app/transactions/page.tsx`
- `frontend/src/features/transactions/hooks.ts`

## 5.4 Alerts

Implemented:

- List open/dismissed alerts
- Filter by assignee and type
- Drawer actions: assign to me, assign member, unassign, acknowledge, dismiss
- Assignment audit trail fetch and display

Hardening in this pass:

- Backend assign/acknowledge payload compatibility to prevent frontend/backend shape mismatch 422.

Primary files:

- `frontend/src/app/app/alerts/page.tsx`
- `frontend/src/features/alerts/hooks.ts`
- `backend/app/api/v1/alerts.py`

## 5.5 Reports

Implemented:

- Async generation dialog
- Job state UI (queued/running/succeeded/failed)
- Existing-report reuse handling
- Download and iframe preview
- Recent report jobs section

Primary files:

- `frontend/src/features/reports/reports-page-client.tsx`
- `frontend/src/features/reports/hooks.ts`

## 5.6 Budgets

Implemented:

- Monthly budget creation by category/type
- Versioned updates
- Variance summary and line table
- Alert refresh queue signal on create/update

Primary files:

- `frontend/src/app/app/budgets/page.tsx`
- `frontend/src/features/budgets/hooks.ts`

## 5.7 Inventory

Implemented:

- Item creation
- Stock event recording
- Purchase order creation
- Forecast risk view (risk badge/stockout projection/cogs exposure)
- Alert refresh queue signal on inventory writes

Primary files:

- `frontend/src/app/app/inventory/page.tsx`
- `frontend/src/features/inventory/hooks.ts`

## 5.8 Settings and admin surfaces

Implemented broad owner/editor controls:

- Org financial thresholds
- Location CRUD/archive/reactivate
- Owner security policy (MFA/session/reauth policy)
- Re-auth token acquisition for sensitive actions
- MFA setup/enable/disable/recovery regeneration
- Session list + revoke actions
- Plan usage and billing controls
- Plaid connect/exchange/sync/revoke UX
- Stripe connect + reconciliation panel
- Member invitation and role assignment
- Account/org deletion requests

Primary files:

- `frontend/src/app/app/settings/page.tsx`
- `frontend/src/features/settings/hooks.ts`

## 5.9 Activity operations console

Implemented:

- Job list and filtering
- Retry/cancel actions
- Outbox monitor and retry
- Scheduler pause/resume/run
- Runtime SLO panel
- Operational diagnostics panel
- Dead-letter replay/dismiss controls
- Audit export download
- PII rotation action
- Deletion lifecycle visibility

Primary files:

- `frontend/src/app/app/activity/page.tsx`
- `frontend/src/features/activity/hooks.ts`

## 5.10 AI chat UX

Implemented:

- Session list
- Chat message composer
- Session creation
- Grounded/fallback indicators per assistant message
- Grounding violation text display when fallback path used

Primary files:

- `frontend/src/app/app/assistant/page.tsx`
- `frontend/src/features/ai-chat/hooks.ts`

## 5.11 Realtime notifications + fallback

Implemented:

- SSE stream client per org
- Reconnect strategy
- fallback polling mode after configurable sustained failures
- live/fallback status shown in notification center
- durable inbox notifications with read/read-all
- session toast history

Primary files:

- `frontend/src/features/notifications/hooks.ts`
- `frontend/src/features/notifications/inbox-hooks.ts`
- `frontend/src/components/shell/notification-center.tsx`

## 6) API Contract Surface Used by Frontend

The frontend already integrates broad backend surface areas:

- auth/mfa/sessions/reauth/deletion
- org settings/members/invites/billing/plan usage
- locations
- transactions/import/import profiles/bulk remap
- analytics/summary/cashflow/budget variance/location benchmark/recompute
- runway/forecast/override
- alerts/history/actions
- reports/generate/download
- jobs/admin/outbox/scheduler/dead-letter/runtime/slo/audit/security
- Plaid bank integrations
- Stripe payment integrations and reconciliation
- inventory APIs
- notifications/events stream
- AI summary and AI chat

Reference file:

- `frontend/src/lib/api/endpoints.ts`

## 7) E2E Coverage Map (Spec-Level)

Available Playwright specs include:

- auth + core flow: `full-flow.spec.ts`, `ops-flow.spec.ts`
- auth mode/security: `cookie-csrf.spec.ts`, `mfa-session.spec.ts`
- realtime resilience: `sse-fallback.spec.ts`
- functional modules: budgets, inventory alerts, alert refresh queue, AI chat, dashboard budget variance
- integrations: Plaid + Stripe specs
- polish/smoke and visual specs

Reference inventory:

- `frontend/e2e/*.spec.ts`

## 8) Current Known Frontend Risks / Improvement Opportunities

1. Some pages are large monolithic components (notably Settings/Transactions/Activity), making UX iteration slower and higher-risk.
2. Several operational controls live in one dense settings/activity surface; first-time owner discoverability is still heavy.
3. Legacy route aliasing exists for compatibility but increases routing surface complexity.
4. Alert-action UX can still be improved by inline validation hints (e.g., non-member assignment) before API roundtrip.
5. Some data grids are plain table blocks; richer progressive disclosure and contextual helper text can reduce onboarding friction.

## 9) Redesign Constraints (Must Keep)

Any AI/designer redesign should preserve these non-negotiables:

1. Strict org scoping (`org_id` context everywhere).
2. RBAC behavior (Owner/Editor/Viewer) exactly preserved.
3. Existing backend API contracts and async job workflows.
4. Cookie and bearer auth mode compatibility.
5. SSE fallback-to-polling resilience behavior.
6. Alert refresh queue semantics shown after write mutations.
7. Integrations surfaces (Plaid/Stripe) and admin controls remain functional.

## 10) Recommended Frontend Refactor Plan (Design-First, Safe)

### Phase A: Information Architecture cleanup (no behavior changes)

- Split Settings into tabs:
  - General
  - Security
  - Integrations
  - Billing
  - Compliance
- Split Activity into tabs:
  - Jobs
  - Outbox
  - Runtime/SLO
  - Dead-letter
  - Security ops

### Phase B: Componentization for maintainability

- Break large pages into feature panels and compose containers.
- Move page-level inline action handlers into feature service hooks.
- Standardize table patterns (header/actions/empty/error/footer).

### Phase C: First-time user comprehension

- Add contextual “what this does” helper callouts for advanced controls.
- Keep onboarding rail persistent until baseline steps complete.
- Add explicit success state cards after first import, first forecast, first report.

### Phase D: UX quality hardening

- Unified inline form validation patterns across all forms.
- Improve optimistic states and mutation progress for long-running operations.
- Add richer role-based affordance text on controls disabled by RBAC.

### Phase E: Design refresh while preserving behavior

- Keep token system, but tighten spacing/typographic hierarchy.
- Introduce stronger visual grouping and progressive disclosure.
- Preserve current color/contrast accessibility guarantees.

## 11) Practical Handover Prompt (for another AI)

Use this as the first prompt for any redesign AI:

"Redesign this frontend UI/UX while preserving all existing behavior/API contracts/RBAC/org isolation. Start by refactoring monolithic pages (`/app/settings`, `/app/activity`, `/app/transactions`) into modular panels, keep all existing endpoints from `frontend/src/lib/api/endpoints.ts`, preserve auth modes (bearer+cookie), preserve SSE fallback behavior, preserve async job progress semantics, and maintain Playwright coverage for all existing specs."

---

This file describes **what exists right now** and what must not be broken during redesign.
