# Epic C Closure Delta (Budgets + Alert Freshness Signal)

## Scope
This delta closes the requested Epic-C hardening slice for alert freshness visibility:
- mutation-time queue feedback in frontend,
- durable queue signal in Notifications/Activity,
- persisted budget-threshold alert verification in Alerts.

## Backend Evidence
- Alert recalc metadata headers added on mutation responses:
  - `backend/app/api/v1/transactions.py:62`
  - `backend/app/api/v1/budgets.py:28`
- Queue-signal notifications emitted (`event=alert.recalc.enqueue`) for transaction/budget writes:
  - `backend/app/api/v1/transactions.py:67`
  - `backend/app/api/v1/budgets.py:33`
- Browser access to queue metadata headers enabled (CORS expose):
  - `backend/app/main.py:31`

## Frontend Evidence
- Mutation hooks read `X-Alert-Recalc-*` metadata:
  - `frontend/src/features/transactions/hooks.ts:66`
  - `frontend/src/features/budgets/hooks.ts:61`
- Transaction and budget UX surfaces queue feedback:
  - `frontend/src/app/app/transactions/page.tsx:193`
  - `frontend/src/app/app/budgets/page.tsx:46`

## Test Evidence
- Backend targeted coverage:
  - `backend/app/tests/test_alerts_budget_threshold.py`
  - `backend/app/tests/test_budgets_endpoint.py`
  - `backend/app/tests/test_transactions_alert_refresh_enqueue.py`
  - `backend/app/tests/test_import_profiles_endpoint.py`
  - `backend/app/tests/test_transactions_jobs_alert_enqueue_integration.py`
- New e2e flow:
  - `frontend/e2e/alert-refresh-queue.spec.ts:3`
  - Flow: transaction mutation -> notification queue signal -> Activity `recalc_alerts` -> Alerts persisted budget-threshold signal.

## Regression Verification (This Run)
- Backend targeted suites:
  - Command: `.venv\\Scripts\\python.exe -m pytest backend/app/tests/test_alerts_budget_threshold.py backend/app/tests/test_budgets_endpoint.py backend/app/tests/test_transactions_alert_refresh_enqueue.py backend/app/tests/test_import_profiles_endpoint.py backend/app/tests/test_transactions_jobs_alert_enqueue_integration.py backend/app/tests/test_jobs_endpoint.py backend/app/tests/test_jobs_commands.py`
  - Result: `18 passed`
- Frontend production build:
  - Command: `npm run build` (frontend)
  - Result: success (`Next.js 15.5.12`)
- Key e2e specs:
  - Command: `npx playwright test e2e/dashboard-budget-variance.spec.ts e2e/alert-refresh-queue.spec.ts e2e/ops-flow.spec.ts e2e/budgets.spec.ts`
  - Result: `10 passed`

## Residual Risks
- Queue feedback currently depends on either response headers or durable notification signal; if either path is disabled in future deployments, UI feedback may degrade to generic success copy.
- Persisted budget-threshold visibility remains dependent on worker/queue health for recompute execution.
