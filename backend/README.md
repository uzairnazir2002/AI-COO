# AI COO Backend

FastAPI async backend with multi-tenant RBAC, JWT auth, Celery jobs, and Postgres.

## Run locally
1. Copy `.env.example` to `.env` and set secrets.
2. Start stack: `docker compose up --build`
3. API docs: `http://localhost:8000/docs`

## Architecture
- API routers: `app/api/v1`
- Services: `app/domain/services`
- Repositories: `app/domain/repos`
- Models: `app/domain/models`
- Worker tasks: `app/jobs/tasks`

## Security defaults
- Argon2id hashing via `argon2-cffi` (time_cost=3, memory_cost=65536, parallelism=2)
- Access token expiry: 15 minutes
- Refresh token expiry: 14 days with rotation + revocation in `token_sessions`
- Registration confirmation token flow (`account_confirmation_tokens`) before first login
- Rate limits on auth routes
- Mandatory org membership checks with 403 on violations
- Audit log for auth and financial events

## Cash balance definition
`cash_balance = organization_settings.starting_cash + sum(revenue) - sum(expenses)`

## Burn / runway definition
- Burn monthly = `max(0, avg(expenses - revenue))`
- Conservative mode uses worst 2 months from lookback.
- Runway days = `(cash_balance / monthly_burn) * 30`, alert when `< 60`.

## CSV import safety
- Max payload size controlled by `CSV_MAX_BYTES`
- Field mapping validated by parser
- Duplicate detection by org/date/amount/type/category/vendor

## Job lifecycle tracking
- Canonical task tracking table: `job_states`
- Lifecycle statuses: `PENDING`, `RUNNING`, `RETRYING`, `SUCCEEDED`, `FAILED`
- Metadata includes `org_id`, `task_id`, `task_name`, `request_id`, `correlation_id`, retry/error fields, and timestamps
- Jobs API: `GET /api/v1/jobs?org_id=...&status=...&task_name=...&since=...&until=...`
- Viewer role gets redacted failure details (`last_error`, `traceback_summary`)

## Outbox reliability
- `outbox_events` stores notification intents in the same DB transaction as business writes
- Celery beat runs `process_outbox` every minute
- Delivery states: `PENDING`, `PROCESSING`, `RETRYING`, `SENT`, `FAILED`
- Dedupe keys prevent duplicate report/invite notification emission

## Refresh token reuse detection
- Rotated sessions persist `replaced_by_token_hash`
- Reuse of an already-rotated refresh token revokes active sessions and writes audit event `auth.refresh.reuse_detected`

## Admin recompute endpoint
- `POST /api/v1/admin/recompute?org_id=...` (OWNER only)
- Enqueues:
  - monthly aggregates rebuild
  - forecast recompute
  - alerts recompute
  - report object verification

## Billing placeholders (owner-only)
- `organization_billing` stores billing contact + placeholder invoice fields.
- Endpoints:
  - `GET /api/v1/organizations/{org_id}/billing`
  - `PUT /api/v1/organizations/{org_id}/billing`

## Realtime updates and polling fallback
- SSE endpoint: `GET /api/v1/events/stream?org_id=...&interval_seconds=...`
- Recommended fallback behavior: poll summary/alerts every 15-30s when SSE is unavailable.

## Plans and usage limits
- `organization_plans` + `usage_meters` enforce soft monthly limits.
- Enforced endpoints:
  - transaction create/import
  - report generation
  - ai summary generation
- Plan usage endpoint:
  - `GET /api/v1/organizations/{org_id}/plan-usage`

## Import history
- `transaction_imports` stores preview/commit import records and row-level error context.
- APIs:
  - `GET /api/v1/transactions/imports?org_id=...`
  - `GET /api/v1/transactions/imports/{import_id}/errors?org_id=...`

## Quality
- Lint: `ruff check app`
- Format: `black app`
- Type check: `mypy app`
- Tests: `pytest app/tests`
