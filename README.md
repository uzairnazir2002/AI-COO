# AI COO (MVP)

Multi-tenant SaaS for SMB operations with FastAPI + Next.js + Celery.

## Monorepo
- `backend/` FastAPI API, SQLAlchemy models, Alembic migrations, tests, jobs
- `worker/` Celery worker/beat container setup
- `frontend/` Next.js App Router UI
- `shared/` shared enums/contracts, OpenAPI artifact
- `docker/` local infra notes
- `docker-compose.yml` full local stack

## Implemented MVP capabilities
- Multi-tenant org/user model with RBAC (`OWNER`, `EDITOR`, `VIEWER`)
- Auth with Argon2id hashing, JWT access/refresh, refresh rotation/revocation
- Optional TOTP MFA for account login plus single-use recovery codes and active session management (list/revoke/revoke-others)
- Owner security policy controls (owner MFA requirement, owner session max age, sensitive-action reauth window)
- Registration confirmation workflow (`POST /api/v1/auth/confirm`) with outbox-backed email token delivery
- Transactions CRUD + CSV import with safe parsing, mapping validation, duplicate detection/skip
- CSV import two-step mode (`commit=false` preview, then `commit=true` apply)
- Transaction bulk category remap + inline edit support
- Dashboard analytics (cash, MTD revenue/expense, net, burn) + cashflow series
- Runway endpoint with lookback + conservative mode + alert threshold `< 60 days`
- Forecast scenarios (`BASE/HIGH/LOW`) + overrides
- Alerts (anomaly + profit leak patterns + runway exposure in summary)
- Weekly PDF report generation, idempotent by `(org_id, week_start)`, stored in MinIO
- Reports API generation endpoint enqueues async Celery jobs and returns immediate job status
- Background jobs: report generation, email dispatch, forecast recalculation
- Standardized task lifecycle tracking in `job_states` (`PENDING/RUNNING/RETRYING/SUCCEEDED/FAILED`)
- Jobs API for org-scoped task visibility and filtering (`GET /api/v1/jobs`)
- Outbox pattern for report/invite notifications with retryable delivery (`outbox_events`)
- Data-protection baseline: encrypted PII fields (billing/invite/session metadata), key rotation endpoint, soft-delete + purge workflow
- Refresh token reuse detection with session family revocation + audit event
- Owner-only admin recompute orchestration endpoint (`POST /api/v1/admin/recompute`)
- AI summary endpoint grounded in computed metrics with schema validation + deterministic fallback
- Onboarding wizard for first org creation
- Invite token acceptance flow (`/register?invite_token=...` -> `/api/v1/auth/invite/accept`)
- Org-level threshold settings for runway and alert sensitivity
- Owner-only billing placeholder management (`GET/PUT /api/v1/organizations/{org_id}/billing`)
- Recompute endpoint to enqueue alerts + forecast refresh
- Plan + usage metering with soft limits (transactions, reports, AI summaries)
- CSV import history with error-row CSV download
- Persistent CSV import mapping profiles (personal/shared) with profile-based import execution
- Real-time stream endpoint (`GET /api/v1/events/stream`) plus polling-safe UX fallback
- Bank integrations foundation (Plaid/Stub provider): link token, token exchange, org-scoped connections, async sync enqueue
- Plaid webhook ingestion with signature verification (`X-Plaid-Signature` + `PLAID_WEBHOOK_SECRET`)
- Automatic bank sync orchestration via Celery Beat (`sync_all_active_bank_connections` every 30 minutes, pauseable with schedule controls)
- Payment integrations foundation (Stripe): org-scoped connect endpoint, signed webhook ingestion, and reconciliation totals vs internal transactions

## Security defaults
- Argon2id password hashing (`time_cost=3`, `memory_cost=65536`, `parallelism=2`)
- Access token short TTL (default 15 minutes)
- Refresh token rotation + revoke-on-logout (`token_sessions` table)
- Dual auth transport:
- `bearer` mode (local/dev): access+refresh tokens in response body
- `cookie` mode (production): HttpOnly auth cookies, token body omitted, CSRF double-submit enforced on mutating requests
- Auth endpoint rate limiting via Redis
- Strict org membership enforcement (`403` for forbidden access)
- Audit logging for auth, org, transaction, import, and report events
- CSV import size limits and strict field/type validation
- HTTPS-only expected in production; local dev HTTP exception documented in `.env.example`

## Performance defaults
- Monthly precomputed aggregates in `monthly_aggregates`
- Indexed hot paths (`org_id`, `date`, `type`, `category`, `created_at`)
- Pagination on transaction list endpoint
- Heavy work moved to Celery jobs

## Key defaults (documented choices)
- Cash balance: `starting_cash + total_revenue - total_expense`
- Burn: `max(0, avg_monthly_expenses - avg_monthly_revenue)` from lookback aggregates
- Conservative burn: average of worst 2 burn months in lookback
- Forecast model: deterministic trailing-average with scenario multipliers
- Worker tech: Celery + Redis + Celery Beat

See ADRs:
- `backend/docs/adr/0001-worker-choice.md`
- `backend/docs/adr/0002-forecast-algorithm.md`
- `backend/docs/adr/0003-cash-balance.md`
- `backend/docs/adr/0004-idempotency.md`
- `backend/docs/adr/0005-job-state-standardization.md`
- `backend/docs/adr/0006-outbox-pattern.md`
- `backend/docs/adr/0007-refresh-token-reuse-detection.md`
- `backend/docs/adr/0008-performance-harness.md`
- `backend/docs/adr/0009-plans-and-usage-metering.md`
- `backend/docs/adr/0010-transaction-import-history.md`
- `backend/docs/adr/0011-registration-confirmation-and-billing.md`
- `backend/docs/adr/0012-realtime-updates-sse-with-polling-fallback.md`

## Local development
1. Copy env file:
   - `cp .env.example .env` (or PowerShell: `Copy-Item .env.example .env`)
2. Start services:
   - `docker compose --env-file .env up --build`
3. Open:
   - Backend Swagger: `http://localhost:8000/docs`
   - Frontend: `http://localhost:3000`
   - MinIO console: `http://localhost:9001`

## Env vars (core)
- `DATABASE_URL`, `REDIS_URL`
- `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_DRY_RUN`
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_API_URL` (optional alias used by frontend API client)
- `AUTH_COOKIE_MODE`, `COOKIE_SECURE`, `COOKIE_SAMESITE`, `ACCESS_COOKIE_NAME`, `REFRESH_COOKIE_NAME`
- `ENFORCE_HTTPS` (optional strict transport enforcement for non-development environments)
- `PII_ENCRYPTION_KEYS`, `PII_ENCRYPTION_ACTIVE_KEY_ID` (PII encryption keyring + active key selector)
- `DELETION_GRACE_PERIOD_DAYS` (soft-delete grace period before purge)
- `AUTH_LOCKOUT_THRESHOLD`, `AUTH_LOCKOUT_WINDOW_MINUTES`, `AUTH_LOCKOUT_DURATION_MINUTES` (login lockout controls)
- `CSRF_COOKIE_NAME`, `CSRF_HEADER_NAME` (cookie mode mutating requests)
- `EXPOSE_INVITE_TOKEN_IN_RESPONSE` (set `false` in production)
- `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE` (optional backend + worker tracing/error capture)
- `NEXT_PUBLIC_AUTH_MODE` (`bearer` for local, `cookie` for production)
- `NEXT_PUBLIC_CSRF_COOKIE_NAME`, `NEXT_PUBLIC_CSRF_HEADER_NAME` (frontend cookie-mode CSRF names)
- `BANK_PROVIDER` (`stub` or `plaid`), `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV`, `PLAID_PRODUCTS`, `PLAID_COUNTRY_CODES`, `PLAID_WEBHOOK_URL`
- `PLAID_WEBHOOK_SECRET` (required for webhook signature verification)
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` (billing + payment ingestion/reconciliation)

## API contract
Prefix: `/api/v1`

Main groups:
- `auth`: register/login/refresh/logout/me/invite-accept/mfa/session-management/reauth/delete-account
  - Development helper: `GET /auth/dev/confirmation-token?email=...` (available only when `ENV=development`)
- `organizations`: create/list/invite/members/settings
- `organizations`: create/list/invite/members/settings/plan-usage/billing
- `transactions`: create/list/update/delete/import-csv/import-history/import-errors/bulk-remap-category
- `transactions`: import profile CRUD (`/transactions/import-profiles`) and profile-referenced import (`profile_id`)
- `analytics`: summary/cashflow/recompute
- `runway`: runway calculator
- `forecast`: get/override
- `alerts`: list/dismiss/assign/acknowledge/history
- `reports`: list/generate/download
- `jobs`: list with status/task/date filters
- `admin`: owner-only recompute orchestration + audit export + org PII rotation
- `events`: SSE stream for summary + alerts updates
- `integrations`: bank connection lifecycle (`/integrations/banks/*`)
  - `POST /integrations/banks/plaid/webhook` (Plaid transaction webhooks -> async sync enqueue)
  - `GET /integrations/payments/connections?org_id=...&provider=STRIPE`
  - `POST /integrations/payments/stripe/connect`
  - `POST /integrations/payments/stripe/webhook`
  - `GET /integrations/payments/reconciliation?org_id=...&date_from=...&date_to=...`
- `ai`: executive summary + chat + provider/fallback health (`GET /api/v1/ai/health?org_id=...&live_check=true`)
- `health`: service checks

OpenAPI export:
- Runtime: `GET /openapi.json`
- Shared artifact: `shared/contracts/openapi/openapi.json`

## Test & quality
Backend:
- `cd backend`
- `..\.venv\Scripts\python.exe -m pytest app/tests -q` (Windows path from backend)

Frontend:
- `cd frontend`
- `npm run lint`
- `npm run build`

One-command checks:
- `make check`
- `make migration-safety` (alembic upgrade/downgrade/re-upgrade smoke)
- `make smoke` (requires running stack)
- `make verify-runtime` (health + backend tests + bearer/cookie smoke + bearer/cookie E2E)
- Cookie-mode smoke: `python scripts/smoke_mvp.py --base-url http://localhost:8000/api/v1 --auth-mode cookie`
- Frontend only: `cd frontend && npm run check`
- Live Plaid sandbox integration test (optional):
  - `RUN_INTEGRATION_LIVE=1 PLAID_SANDBOX_E2E=1 PLAID_CLIENT_ID=... PLAID_SECRET=... .\\.venv\\Scripts\\python.exe -m pytest backend/app/tests/test_plaid_sandbox_live.py -q`
- Live Stripe test-mode webhook integration test (optional):
  - `RUN_INTEGRATION_LIVE=1 STRIPE_SANDBOX_E2E=1 STRIPE_SECRET_KEY=... STRIPE_WEBHOOK_SECRET=... .\\.venv\\Scripts\\python.exe -m pytest backend/app/tests/test_stripe_sandbox_live.py -q`

## Acceptance Evidence (March 5, 2026)
- Backend tests:
  - command: `cd backend && ..\.venv\Scripts\python.exe -m pytest app/tests -q`
  - result: `28 passed, 2 skipped`
- Frontend quality:
  - command: `cd frontend && npm run lint && npm run build`
  - result: clean lint + successful production build
- Frontend E2E:
  - command: `cd frontend && npx playwright test --workers=1 --retries=0`
  - result: `4 passed, 7 skipped`
  - skip reasons:
  - `cookie-csrf.spec.ts` is skipped unless `E2E_AUTH_MODE=cookie`
  - `visual.spec.ts` tests are skipped unless `E2E_VISUAL=1`
- Runtime services:
  - `docker compose --env-file .env up --build -d`
  - `GET http://localhost:8000/api/v1/health -> {"ok":true,"db":true,"redis":true}`

Full runtime verification (manual command):
```bash
python scripts/verify_runtime.py --api-base-url http://localhost:8000/api/v1 --frontend-base-url http://localhost:3000
```

AI live-mode verification (manual command):
```bash
python scripts/ops/verify_ai_live_mode.py --api-base-url http://localhost:8000/api/v1 --database-url postgresql://ai_coo:ai_coo@localhost:5432/ai_coo --live-check --verify-fallback-test
```

Secret hygiene audit (manual command):
```bash
python scripts/ops/secret_hygiene_audit.py --root . --env-file .env.example
```

## Demo data seed (6 months)
Use `shared/demo/transactions_6months.csv` with the transactions CSV import endpoint to generate realistic trends for anomaly/profit-leak/forecast output.

Example import:
```bash
curl -X POST http://localhost:8000/api/v1/transactions/import/csv \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "org_id=<ORG_ID>" \
  -F 'mapping={"date":"date","amount":"amount","type":"type","category":"category","vendor":"vendor","notes":"notes"}' \
  -F "file=@shared/demo/transactions_6months.csv"
```

## Production hardening checklist
- Rotate `SECRET_KEY` and all DB/Redis/S3/SMTP credentials.
- Keep `CORS_ORIGINS` restricted to the frontend origin only.
- Keep `EMAIL_DRY_RUN=true` until SMTP verification is complete.
- Place backend behind an HTTPS reverse proxy (Nginx/Traefik/Caddy) and terminate TLS there.
- Reference Nginx config: `docker/nginx/default.conf`
- Backup/restore runbook: `docs/operations/backup_restore.md`
- Privacy/deletion operations runbook: `docs/operations/privacy_deletion.md`
- AI live-mode runbook: `docs/operations/ai_live_mode.md`
- Secret hygiene checklist: `docs/operations/secret_hygiene_checklist.md`
- CI env-gated lanes: `docs/operations/ci_env_gated_lanes.md`
- Performance harness docs: `docs/performance.md`

## API examples
Register:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"Password123!"}'
```

Login:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"Password123!"}'
```

Confirm account (after register, token is delivered via outbox email transport/stub):
```bash
curl -X POST http://localhost:8000/api/v1/auth/confirm \
  -H "Content-Type: application/json" \
  -d '{"token":"<CONFIRM_TOKEN>"}'
```

Create org:
```bash
curl -X POST http://localhost:8000/api/v1/organizations \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme LLC"}'
```

Generate report:
```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate?org_id=<ORG_ID>&week_start=2026-03-02" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
Response includes `job_id`, `status`, and `report_id` when an existing report is reused.
