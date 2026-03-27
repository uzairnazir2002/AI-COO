# Epic A Closure Delta (Plaid Integration)

## Scope
This delta closes Epic A for Plaid bank integration with verified API, worker dispatch, webhook ingestion, and frontend management UX.

## Regression Verification (Rebuilt Containers)
- Backend full suite (container):
  - Command: `docker compose --env-file .env exec -T backend sh -lc "cd /app && pytest app/tests -q"`
  - Result: `163 passed, 3 skipped`
- Frontend full Playwright suite:
  - Command: `npm run e2e`
  - Result: `13 passed, 9 skipped`
- Frontend production build:
  - Command: `npm run build`
  - Result: success (`Next.js 15.5.12`)

## API Evidence
- Plaid Link token endpoint: `POST /api/v1/integrations/banks/plaid/link-token`
  - `backend/app/api/v1/integrations.py:63`
- Plaid public token exchange: `POST /api/v1/integrations/banks/plaid/exchange`
  - `backend/app/api/v1/integrations.py:77`
- List bank connections: `GET /api/v1/integrations/banks/connections`
  - `backend/app/api/v1/integrations.py:96`
- Revoke connection: `DELETE /api/v1/integrations/banks/{connection_id}`
  - `backend/app/api/v1/integrations.py:112`
- Manual sync enqueue: `POST /api/v1/integrations/banks/{connection_id}/sync`
  - `backend/app/api/v1/integrations.py:127`
- Plaid webhook ingestion + signature validation path:
  - `backend/app/api/v1/integrations.py:173`

## Service/Worker Evidence
- Provider/service orchestration implemented:
  - link token: `backend/app/domain/services/bank_integration_service.py:48`
  - token exchange: `backend/app/domain/services/bank_integration_service.py:60`
  - connection revoke: `backend/app/domain/services/bank_integration_service.py:87`
  - sync execution: `backend/app/domain/services/bank_integration_service.py:105`
- Async tracked task dispatch and retries for sync:
  - `backend/app/jobs/tasks/banks.py`

## Frontend UX Evidence
- Plaid integration section in Settings page:
  - `frontend/src/app/app/settings/page.tsx:668`
- Connect with Plaid action:
  - `frontend/src/app/app/settings/page.tsx:685`
- Manual exchange flow with pending state:
  - `frontend/src/app/app/settings/page.tsx:723`
- Connection loading/error UX:
  - `frontend/src/app/app/settings/page.tsx:730`
  - `frontend/src/app/app/settings/page.tsx:733`
- Per-connection sync/revoke in-progress button states:
  - sync button state: `frontend/src/app/app/settings/page.tsx:769`
  - revoke button state: `frontend/src/app/app/settings/page.tsx:791`

## Test Evidence
- Live Plaid sandbox e2e (backend integration test):
  - `backend/app/tests/test_plaid_sandbox_live.py:39`
- API endpoint integration tests:
  - `backend/app/tests/test_integrations_endpoint.py:159`
  - `backend/app/tests/test_integrations_webhook.py:85`
  - `backend/app/tests/test_integrations_webhook.py:97`
- Frontend Playwright Plaid flow spec:
  - `frontend/e2e/plaid-integration.spec.ts:9`

## Playwright Pass/Skip Matrix (Latest Full Run)
- `e2e/full-flow.spec.ts`: PASS
- `e2e/mfa-session.spec.ts`: PASS
- `e2e/ops-flow.spec.ts`: PASS
- `e2e/polish.spec.ts`: PASS
- `e2e/cookie-csrf.spec.ts`: SKIP (env-gated)
- `e2e/plaid-integration.spec.ts`: SKIP (requires `E2E_PLAID_SANDBOX=1` and `E2E_PLAID_PUBLIC_TOKEN`)
- `e2e/sse-fallback.spec.ts`: SKIP (env/fixture-gated)
- `e2e/visual.spec.ts`: SKIP (visual mode-gated)

## Residual Risks
- Playwright Plaid UI spec is env-gated and was skipped in full-suite default run; run with sandbox token env to include it in CI gate.
- Webhook signature + sync enqueue are covered by integration tests, but production webhook delivery behavior still depends on external network/event timing.
- Provider dependency risk remains (Plaid sandbox/live availability and credential rotation).
