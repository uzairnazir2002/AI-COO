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

## Quality
- Lint: `ruff check app`
- Format: `black app`
- Type check: `mypy app`
- Tests: `pytest app/tests`
