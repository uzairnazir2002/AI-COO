# Stage-1 P1 Traceability Delta

Date: 2026-03-25

## Status matrix (requested items)

| Item | Status | Evidence |
|---|---|---|
| Stage-1 P0: Owner policy controls (session timeout, mandatory owner MFA, sensitive-action re-auth enforcement) | COMPLETE | `backend/app/api/deps.py`, `backend/app/api/v1/organizations.py`, `backend/app/domain/models/organization_setting.py`, `frontend/src/app/app/settings/page.tsx`, `frontend/src/features/settings/hooks.ts`, `backend/app/tests/test_owner_policy_deps.py`, `backend/app/tests/test_org_security_policy_endpoint.py` |
| Stage-1 P0: Brute-force lockout escalation telemetry/audit | COMPLETE | `backend/app/core/auth_lockout.py`, `backend/app/api/v1/auth.py`, `backend/app/api/v1/admin.py`, `backend/app/domain/schemas/operations.py`, `frontend/src/app/app/activity/page.tsx`, `backend/app/tests/test_auth_lockout_metrics.py`, `backend/app/tests/test_auth_lockout_endpoint.py` |
| Global frontend error UX consistency (auth/network/CORS) | COMPLETE | `frontend/src/lib/api/client.ts`, `frontend/src/components/common/global-api-feedback.tsx`, `frontend/src/features/activity/hooks.ts`, `frontend/src/features/transactions/hooks.ts`, `frontend/src/features/notifications/hooks.ts` |
| Owner/admin runbook expansion | COMPLETE | `docs/operations/owner_admin_runbook.md`, `docs/operations/worker_resilience.md` |
| Owner/admin diagnostics panel (failed jobs, outbox retries, SLO/lag breach, DLQ replay) | COMPLETE | `frontend/src/app/app/activity/page.tsx`, `backend/app/api/v1/admin.py`, `backend/app/domain/repos/dead_letter_repo.py` |
| Epic-C alert freshness UX + persisted threshold coverage (mutation -> queue signal -> alerts persistence) | COMPLETE | `backend/app/api/v1/transactions.py:62`, `backend/app/api/v1/budgets.py:28`, `backend/app/main.py:31`, `frontend/src/features/transactions/hooks.ts:66`, `frontend/src/features/budgets/hooks.ts:61`, `frontend/src/app/app/transactions/page.tsx:193`, `frontend/src/app/app/budgets/page.tsx:46`, `frontend/e2e/alert-refresh-queue.spec.ts:3` |

## Completed in this change set

### Operational resilience depth
- Dead-letter persistence introduced for terminal outbox and job failures.
  - Model: `backend/app/domain/models/dead_letter_event.py`
  - Migration: `backend/migrations/versions/0020_dead_letter_events.py`
  - Failure recording:
    - `backend/app/domain/repos/outbox_repo.py` (`mark_retry_or_failed`)
    - `backend/app/jobs/task_tracking.py` (`mark_failed`)
- Owner replay/dismiss tooling added:
  - `GET /api/v1/admin/dead-letter`
  - `POST /api/v1/admin/dead-letter/{id}/replay`
  - `POST /api/v1/admin/dead-letter/{id}/dismiss`
  - File: `backend/app/api/v1/admin.py`

### Queue lag / worker health alerting extension
- Runtime metrics now include:
  - `queue_lag_seconds`
  - `queue_lag_breach`
  - `dead_letter_open`
  - `worker_health`
- Files:
  - `backend/app/domain/repos/job_repo.py` (oldest active job timestamp)
  - `backend/app/domain/schemas/operations.py`
  - `backend/app/core/config.py` (`RUNTIME_QUEUE_LAG_THRESHOLD_SECONDS`)
  - `backend/app/api/v1/admin.py`

### Owner/admin diagnostics UX
- Activity page now exposes a consolidated operational diagnostics surface:
  - Runtime health cards
  - Dead-letter list + replay + dismiss actions
- Files:
  - `frontend/src/features/activity/hooks.ts`
  - `frontend/src/lib/api/endpoints.ts`
  - `frontend/src/lib/api/schemas.ts`
  - `frontend/src/app/app/activity/page.tsx`

### Frontend global error UX consistency pass
- Remaining direct authenticated client fetch paths were moved to shared auth/network/error handling:
  - `downloadImportErrors` now uses `apiFetchRaw`
  - `audit export` now uses `apiFetchRaw`
- SSE stream now emits session-expired global event on `401` to avoid inconsistent fallback-only behavior.
- Files:
  - `frontend/src/lib/api/client.ts` (`apiFetchRaw`)
  - `frontend/src/features/transactions/hooks.ts`
  - `frontend/src/features/activity/hooks.ts`
  - `frontend/src/features/notifications/hooks.ts`

### Runbook expansion
- Added owner/admin operational runbook for DLQ triage, outbox retry, lag/SLO response, and compliance actions.
- File:
  - `docs/operations/owner_admin_runbook.md`

### Epic-C delta: alert refresh queue feedback and visibility
- Added alert-recalc response metadata headers for transaction/budget/import/remap mutations:
  - `X-Alert-Recalc-Task-Id`
  - `X-Alert-Recalc-Status`
  - `X-Alert-Recalc-Queued`
- Exposed the headers in CORS for browser clients:
  - `backend/app/main.py:31`
- Added durable org notification emission on enqueue (`event=alert.recalc.enqueue`) for:
  - transaction create/update/delete/import commit/bulk remap
  - budget create/update
- Frontend now surfaces mutation-level feedback (`Alert refresh queued/already pending`) in:
  - transactions UX
  - budgets UX
- Added end-to-end flow proving:
  - mutation emits queue signal in notifications
  - tracked `recalc_alerts` job visible in Activity
  - persisted budget-threshold alert visible in Alerts
  - Spec: `frontend/e2e/alert-refresh-queue.spec.ts`

### Stage-1 P0 closure update: brute-force lockout escalation telemetry/audit
- Added escalation levels and escalation counters to auth lockout tracking.
- Added escalation audit event (`auth.login.lockout.escalated`) and escalation metadata on lock/failed events.
- Extended admin runtime metrics with `auth_lockout_escalations_total`.
- Surfaced lockout escalation count in owner Activity operational diagnostics.
- Files:
  - `backend/app/core/auth_lockout.py`
  - `backend/app/api/v1/auth.py`
  - `backend/app/api/v1/admin.py`
  - `backend/app/domain/schemas/operations.py`
  - `frontend/src/lib/api/schemas.ts`
  - `frontend/src/app/app/activity/page.tsx`

## Validation evidence
- Backend tests:
  - `backend/app/tests/test_admin_operations.py`
  - `backend/app/tests/test_outbox_dead_letter.py`
  - `backend/app/tests/test_owner_policy_deps.py`
  - `backend/app/tests/test_org_security_policy_endpoint.py`
  - `backend/app/tests/test_auth_lockout_metrics.py`
  - `backend/app/tests/test_auth_lockout_endpoint.py`
  - `backend/app/tests/test_alerts_budget_threshold.py`
  - `backend/app/tests/test_budgets_endpoint.py`
  - `backend/app/tests/test_transactions_alert_refresh_enqueue.py`
  - `backend/app/tests/test_import_profiles_endpoint.py`
  - `backend/app/tests/test_transactions_jobs_alert_enqueue_integration.py`
  - `backend/app/tests/test_jobs_endpoint.py`
  - `backend/app/tests/test_jobs_commands.py`
- Frontend compile/type validation:
  - `npm run build` in `frontend/`
- Key Playwright slice:
  - `npx playwright test e2e/dashboard-budget-variance.spec.ts e2e/alert-refresh-queue.spec.ts e2e/ops-flow.spec.ts e2e/budgets.spec.ts`

## Playwright full-suite matrix (2026-03-25)

Run command:
- `npm run e2e` (from `frontend/`)

Summary:
- Passed: `13`
- Failed: `0`
- Skipped: `8`

| Spec file | Status | Notes |
|---|---|---|
| `e2e/full-flow.spec.ts` | PASS | Core end-to-end auth->dashboard->transactions->reports flow green |
| `e2e/mfa-session.spec.ts` | PASS | MFA and session API smoke green |
| `e2e/ops-flow.spec.ts` | PASS | Registration/confirmation/invite/activity/settings/alias/return-to flows green |
| `e2e/polish.spec.ts` | PASS | CSV guard, bulk remap, forecast override, RBAC polish checks green |
| `e2e/cookie-csrf.spec.ts` | SKIP | Skipped by spec runtime gating (cookie-mode-specific) |
| `e2e/sse-fallback.spec.ts` | SKIP | Skipped by spec runtime gating (env/stream conditions) |
| `e2e/visual.spec.ts` | SKIP | Visual snapshots skipped (6 cases: dashboard/transactions/reports in light+dark) |
