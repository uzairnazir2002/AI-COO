# Frontend Complete Improvement Plan (Functional + UX)

Date: 2026-03-27

## Audit Evidence
- Frontend build: `npm run build` -> PASS (`Next.js 15.5.12`)
- Full Playwright run: `expected=19, skipped=9, unexpected=0, flaky=0`
- App route inventory:
  - `/app/activity`
  - `/app/alerts`
  - `/app/assistant`
  - `/app/budgets`
  - `/app/dashboard`
  - `/app/forecast`
  - `/app/inventory`
  - `/app/onboarding`
  - `/app/orgs`
  - `/app/reports`
  - `/app/settings`
  - `/app/transactions`

---

## Functional Status Matrix (Frontend)

| Area | Route(s) | Current status | Evidence | Notes |
|---|---|---|---|---|
| Auth | `/auth/login`, `/auth/register`, `/auth/confirm` | WORKING | `ops-flow.spec.ts` | Core auth flow verified |
| Org setup | `/app/orgs`, `/app/onboarding` | PARTIAL-VERIFIED | route code present; limited direct e2e assertions | Needs stronger e2e for first-run org creation + onboarding progression |
| Dashboard | `/app/dashboard` | WORKING | `full-flow.spec.ts`, `dashboard-budget-variance.spec.ts` | KPI/charts/alerts/AI panel flow validated |
| Transactions + CSV | `/app/transactions` | WORKING | `full-flow.spec.ts`, `polish.spec.ts`, `alert-refresh-queue.spec.ts` | Verified after deterministic modal action fix |
| Forecast | `/app/forecast` | WORKING | `full-flow.spec.ts`, `polish.spec.ts` | Override save/reset validated |
| Alerts | `/app/alerts` | WORKING | `alert-refresh-queue.spec.ts`, `inventory-alerts.spec.ts` | Assignment/ack flow present |
| Reports | `/app/reports` | WORKING | `full-flow.spec.ts` | Async generation + job visibility validated |
| Settings core | `/app/settings` | WORKING | `ops-flow.spec.ts`, `mfa-session.spec.ts` | Large feature surface; functionally broad |
| Stripe integration UI | `/app/settings` | WORKING | `stripe-integration.spec.ts` | Live webhook/reconciliation flow passed |
| Plaid integration UI | `/app/settings` | ENV-GATED | `plaid-integration.spec.ts` (skipped unless sandbox env set) | Not validated in default run |
| Budgets | `/app/budgets` | WORKING | `budgets.spec.ts`, `dashboard-budget-variance.spec.ts` | CRUD + variance behavior covered |
| Inventory | `/app/inventory` | WORKING | `inventory-alerts.spec.ts` | Item/stock/forecast alert path validated |
| AI Chat | `/app/assistant` | WORKING | `ai-chat.spec.ts` | Session + grounded/fallback indicator validated |
| Activity/ops console | `/app/activity` | WORKING | `ops-flow.spec.ts`, `alert-refresh-queue.spec.ts`, `inventory-alerts.spec.ts` | Operational diagnostics path exercised |
| SSE fallback | event-driven dashboard hooks | ENV-GATED | `sse-fallback.spec.ts` | Needs dedicated env-enabled run |
| Cookie + CSRF mode | auth/api client | ENV-GATED | `cookie-csrf.spec.ts` | Needs cookie-mode CI lane |
| Visual regressions | key pages | ENV-GATED | `visual.spec.ts` | Not run in default pipeline |

---

## Is Frontend “Completely Working”?

Short answer: **core product flows are working**, but not yet “completely proven” for all runtime modes.

What is solid:
- Main user journeys pass: auth, dashboard, transactions/import, forecast, budgets, alerts, reports, inventory, AI chat.
- Build and type checks are stable.
- Global auth/session/network error handling exists (`GlobalApiFeedback`, shared API client).

What remains to be fully proven:
- Env-gated flows are not always validated in standard runs:
  - Plaid flow
  - Cookie-mode CSRF flow
  - SSE degradation/recovery flow
  - Visual regressions
- First-time onboarding journey needs deeper deterministic e2e coverage (org create -> onboarding checklist completion).

---

## UX Flow Findings (First-Time User Perspective)

### Strengths
- Dedicated onboarding page with readiness checklist.
- Consistent shell navigation and org/location switchers.
- Empty states exist on most pages.
- Strong operational transparency in Activity page.

### Friction Points
1. Settings and Activity pages are very dense for first-time users.
2. Import wizard actions can sit below viewport in smaller viewports; action affordance should be sticky and obvious.
3. Navigation is feature-rich but cognitively heavy on day-1 (12 major sections immediately visible).
4. No guided “happy path” onboarding progression across pages (transactions -> forecast -> report).
5. Env-gated integration panels can confuse users when credentials are not configured.

---

## Complete Improvement Plan

## P0 (Immediate: 1-2 sprints)
1. First-time UX hardening
- Add a persistent onboarding progress rail (top-level) with 3 primary outcomes:
  - Load transactions
  - Review forecast/alerts
  - Generate first report
- Auto-redirect first-time orgs to onboarding until minimum readiness is reached.
- Add “why this is empty” contextual hints on dashboard/forecast/alerts/reports.

Acceptance:
- New user can complete first value loop in < 5 minutes with no docs.

2. Import wizard usability hardening
- Make import modal footer sticky (`Preview`/`Confirm`) and always visible.
- Add stepper UI: File -> Mapping -> Preview -> Confirm.
- Add validation summary block pinned above CTA buttons.

Acceptance:
- No action buttons can be outside viewport on standard laptop sizes.

3. Test coverage closure for unproven modes
- Add dedicated CI jobs:
  - cookie-mode auth/CSRF lane
  - SSE lane
  - Plaid/Stripe integration lane (secrets-gated)
  - visual snapshot lane

Acceptance:
- Every env-gated spec has at least scheduled/nightly execution and artifact retention.

## P1 (Near-term: 2-4 sprints)
1. Information architecture simplification
- Group sidebar into sections:
  - Core: Dashboard, Transactions, Forecast, Alerts, Reports
  - Planning: Budgets, Inventory
  - Ops/Admin: Activity, Settings, Assistant
- Collapse low-frequency admin modules behind expandable group.

2. Settings page redesign
- Split giant settings page into tabbed sub-sections:
  - General
  - Security
  - Billing
  - Integrations
  - Team
  - Compliance
- Preserve current API behavior; improve discoverability only.

3. Activity page progressive disclosure
- Default to concise summary cards.
- Move advanced diagnostics (DLQ, scheduler internals) to expandable panels.

Acceptance:
- Fewer than 3 scroll screens to complete common settings tasks.

## P2 (Next-level polish: 4-8 sprints)
1. Role-based UX refinement
- Render role-scoped quick actions and hide non-actionable controls by default.
- Add “why unavailable” tooltips for restricted actions.

2. Accessibility and keyboard depth
- Full keyboard paths for data entry and modal workflows.
- Improve aria labels and live-region announcements for async statuses.

3. Product analytics for UX tuning
- Track onboarding funnel and per-page task completion events.
- Use drop-off data to tune copy, defaults, and action placement.

Acceptance:
- Improved first-session completion rate and reduced support friction.

---

## Page-by-Page Implementation Backlog

| Page | Priority changes |
|---|---|
| Onboarding | Add hard progression state + explicit completion banner |
| Orgs | Add “Create + continue” wizard microcopy and empty-data preview |
| Dashboard | Add guided CTA when all KPIs are empty |
| Transactions | Sticky import action footer + stronger mapping summary |
| Forecast | Show prerequisite state with direct transaction import CTA |
| Alerts | Add quick triage shortcuts + assignment filters persisted in URL |
| Reports | Add clearer queued/running/completed timeline with elapsed time |
| Settings | Convert to tabbed IA + integration readiness indicators |
| Activity | Split “operator mode” advanced diagnostics behind accordion |
| Inventory | Add item templates and first-stock-event helper |
| Budgets | Add guided monthly setup defaults for first budget |
| Assistant | Add “suggested prompts” starter chips and source links |

---

## Execution Order Recommendation
1. P0 first-time flow + import wizard UX
2. P0 env-gated CI lanes
3. P1 settings/activity IA cleanup
4. P1 navigation grouping
5. P2 accessibility + analytics

---

## P0 Implementation Delta (2026-03-27)
- Implemented guided onboarding progression rail in app shell for incomplete orgs (non-blocking, no hard redirects).
- Refactored onboarding page to consume shared onboarding progression hook.
- Implemented sticky CSV import wizard action footer with pinned validation summary and stable CTA placement.
- Added env-gated CI lanes in `ci.yml` for:
  - cookie-mode CSRF Playwright spec
  - SSE fallback Playwright spec
  - visual Playwright spec
  using repository vars (`CI_E2E_COOKIE_LANE`, `CI_E2E_SSE_LANE`, `CI_E2E_VISUAL_LANE`) or workflow dispatch inputs.
- Added/updated Playwright coverage:
  - onboarding rail visibility for fresh org bootstrap
  - sticky import footer visibility in CSV mapping flow

### Full Playwright Pass/Fail Matrix (Rebuilt Stack)
- Command: `npx playwright test --reporter=json > playwright-report-full.json`
- Run date: 2026-03-27
- Totals: `expected=20`, `skipped=9`, `unexpected=0`, `flaky=0`

| Spec file | Total tests | Passed | Failed | Skipped | Status |
|---|---:|---:|---:|---:|---|
| `ai-chat.spec.ts` | 1 | 1 | 0 | 0 | PASS |
| `alert-refresh-queue.spec.ts` | 1 | 1 | 0 | 0 | PASS |
| `budgets.spec.ts` | 1 | 1 | 0 | 0 | PASS |
| `cookie-csrf.spec.ts` | 1 | 0 | 0 | 1 | SKIPPED (env-gated) |
| `dashboard-budget-variance.spec.ts` | 1 | 1 | 0 | 0 | PASS |
| `full-flow.spec.ts` | 1 | 1 | 0 | 0 | PASS |
| `inventory-alerts.spec.ts` | 1 | 1 | 0 | 0 | PASS |
| `mfa-session.spec.ts` | 1 | 1 | 0 | 0 | PASS |
| `ops-flow.spec.ts` | 7 | 7 | 0 | 0 | PASS |
| `plaid-integration.spec.ts` | 1 | 0 | 0 | 1 | SKIPPED (env-gated) |
| `polish.spec.ts` | 5 | 5 | 0 | 0 | PASS |
| `sse-fallback.spec.ts` | 1 | 0 | 0 | 1 | SKIPPED (env-gated) |
| `stripe-integration.spec.ts` | 1 | 1 | 0 | 0 | PASS |
| `visual.spec.ts` | 6 | 0 | 0 | 6 | SKIPPED (env-gated) |

### Env-Gated CI Lane Validation
- Enabled repository variable: `CI_E2E_COOKIE_LANE=1`.
- Triggered initial CI workflow on branch `sub-branch` with cookie lane input.
  - Run URL: `https://github.com/uzairnazir2002/AI-COO/actions/runs/23615860967`
  - Cookie lane job executed, failed on CSRF bootstrap in auth fixture.
  - Artifact upload validated:
    - Artifact name: `playwright-cookie-csrf-report`
    - Artifact ID: `6132112247`
- Patched cookie-mode fixture CSRF header injection and re-ran CI.
  - Run URL: `https://github.com/uzairnazir2002/AI-COO/actions/runs/23616346624`
  - Cookie lane job URL: `https://github.com/uzairnazir2002/AI-COO/actions/runs/23616346624/job/68784676842`
  - Cookie lane conclusion: `success`
  - Artifact upload validated:
    - Artifact name: `playwright-cookie-csrf-report`
    - Artifact ID: `6132418474`
- Note: full workflow remains red due unrelated jobs (`backend`, `precommit`, `migration-safety`), but cookie-lane spec + artifact pipeline is now healthy.
