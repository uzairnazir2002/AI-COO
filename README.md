# AI COO

AI COO is a multi-tenant operations platform for small and medium businesses. It combines transactions, financial dashboards, cash runway, forecasts, budgets, locations, inventory risk, employee management, attendance, leave, payroll, HR policies, internal communications, alerts, weekly PDF reports and an AI assistant. Owners also manage membership, security policies, integrations, billing and background operations.

The monorepo uses Next.js, FastAPI, PostgreSQL, Redis, Celery and MinIO. Application packages are version `0.1.0`. The original MVP expanded through Plaid, Stripe, budgets, multiple locations, inventory and AI chat, followed by a frontend redesign, Workforce/HR workflows and confirmation-email improvements.

This README describes the repository reevaluated on **September 15, 2026**, at branch HEAD **`66ac1e7`** (`fixes`). The current source inventory contains **957 tracked files, 185 API routes across 29 leaf route modules, 91 backend settings, 64 database tables/models, 208 schema classes, 40 migrations and 109 backend test files**. Implementation, historical test evidence and deployment readiness are distinguished. Appendices provide a complete reference for routes, configuration, database models, schemas, source modules, migrations, tests and supporting assets. Private environment values and stored tokens are excluded.

## Contents

- [Product and workflows](#product-and-workflows)
- [Architecture and repository](#architecture-and-repository)
- [Technology](#technology)
- [Local setup](#local-setup)
- [Authentication and security](#authentication-and-security)
- [Confirmation and email delivery](#confirmation-and-email-delivery)
- [Workforce and HR](#workforce-and-hr)
- [Financial calculations](#financial-calculations)
- [Transactions and imports](#transactions-and-imports)
- [Budgets, locations, inventory and alerts](#budgets-locations-inventory-and-alerts)
- [Reports and background operations](#reports-and-background-operations)
- [AI summaries and chat](#ai-summaries-and-chat)
- [Integrations, billing and quotas](#integrations-billing-and-quotas)
- [API conventions and examples](#api-conventions-and-examples)
- [Frontend](#frontend)
- [Database and configuration](#database-and-configuration)
- [Testing and CI](#testing-and-ci)
- [Performance and observability](#performance-and-observability)
- [Deployment and operations](#deployment-and-operations)
- [Troubleshooting and limitations](#troubleshooting-and-limitations)
- [Complete implementation reference](#complete-implementation-reference)

## Product and workflows

| Area | Implemented capabilities |
| --- | --- |
| Accounts | Registration/confirmation/resend, login/refresh/logout, current user, invite acceptance, MFA/recovery, session management, reauth, deletion requests |
| Organizations | Create/switch, membership/invitations/roles, thresholds, owner policy, plan/usage, billing/deletion visibility |
| Dashboard | Cash, MTD revenue/expense/net/burn, cashflow, budget variance, location benchmark, alerts and AI |
| Transactions | CRUD, search/filters/pagination, inline editing, category remap, CSV preview/commit/profiles/history/error download |
| Budgets | Monthly revenue/expense category budgets, versions/history, variance and threshold alerts |
| Locations | Org-owned locations, edit/archive/reactivate, supported scoped views and benchmarks |
| Inventory | Items/SKU/cost/reorder points, stock movements, purchase orders, velocity, cover/stockout risk |
| Forecast | BASE/HIGH/LOW scenarios, heuristic bands, saved overrides and recalculation |
| Alerts | Anomaly/profit leak/budget/inventory signals, assignment/unassignment/acknowledge/dismiss/history |
| Reports | Async weekly PDF generation/reuse, progress, preview/download and email outbox |
| AI assistant | Persistent sessions/messages, KPI/alert-grounded answers, fallback/violation metadata |
| Integrations | Stub/Plaid links/sync, Stripe payments/reconciliation, subscription checkout/portal |
| Operations | Jobs/retry/cancel, outbox/retry, schedules, metrics/SLO/diagnostics, dead letters, audit, PII rotation/deletion |
| Workforce | Employees, departments, titles, shifts, daily/monthly attendance, correction requests, leave types/balances/approvals, payroll periods/entries/payslips |
| HR and communications | Policies/versioning/acknowledgments, employee documents, onboarding/offboarding checklists, targeted announcements, templates, attachments, delivery tracking and scheduled publication |
| Workforce intelligence | Dashboard KPIs, attendance/leave/payroll/headcount reports, JSON export, operational alerts and AI grounding context |
| Notifications | Durable read/read-all inbox, SSE snapshots, reconnect/polling fallback and toast history |

First use: register/confirm or accept an invite, log in, create an organization, complete onboarding, set starting cash/thresholds/locations, enter or import transactions, review metrics, add budgets/inventory, assign alerts and generate reports. For Workforce, configure departments/titles/shifts, create employees and compensation, record attendance, allocate leave, approve requests, generate/review/approve payroll and record payment. Publish policies and announcements, then review acknowledgments, deliveries and workforce intelligence. Settings manages organization configuration; Operations shows everyday runtime activity and Admin Console exposes advanced administration. Provider features require credentials; default bank/AI are stubs and email is dry run.

## Architecture and repository

```mermaid
flowchart LR
    Browser[Browser] --> UI[Next.js :3000]
    Browser --> API[FastAPI /api/v1 :8000]
    UI --> API
    API --> PG[(PostgreSQL :5432)]
    API --> Redis[(Redis :6379)]
    API --> S3[(MinIO :9000)]
    Beat[Celery Beat UTC] --> Redis
    Redis --> Worker[Celery worker]
    Worker --> PG
    Worker --> S3
    Worker --> Mail[SMTP / Resend / dry run]
    API --> Providers[AI / Plaid / Stripe]
    Worker --> Providers
```

Routes validate/authenticate and enforce organization access; services implement business rules; repositories query SQLAlchemy models. Infrastructure adapters handle Redis, S3, SMTP/Resend and AI HTTP. Celery separates heavy work from requests while PostgreSQL stores tracking/outbox state.

| Path | Responsibility |
| --- | --- |
| `backend/app/api/` | Auth dependencies and versioned routes |
| `backend/app/core/` | Settings/security/MFA/crypto/middleware/telemetry |
| `backend/app/db/` | ORM base, async sessions and migration helpers |
| `backend/app/domain/models/` | Persistent entities |
| `backend/app/domain/schemas/` | Pydantic contracts |
| `backend/app/domain/repos/` | Persistence/queries |
| `backend/app/domain/services/` | Business logic/orchestration |
| `backend/app/infra/` | Redis/AI/email/S3 adapters |
| `backend/app/jobs/` | Celery configuration/tracking/tasks |
| `backend/app/tests/`, `backend/app/utils/` | Tests and CSV/time/money/idempotency helpers |
| `backend/migrations/`, `backend/scripts/`, `backend/docs/adr/` | 40 revisions, safety checker and decisions |
| `frontend/src/app/` | Public/auth/protected routes/aliases |
| `frontend/src/components/` | Shell/UI/charts/KPIs/feedback |
| `frontend/src/features/` | Feature hooks/client pages |
| `frontend/src/lib/`, `src/store/`, `src/types/` | API/auth/queries/utils, Zustand and types |
| `frontend/e2e/` | Playwright specs/fixtures |
| `worker/`, `shared/` | Worker container; shared role/OpenAPI/demo data |
| `docker/`, `bridge/` | Service/proxy notes; generated Kubernetes resources |
| `scripts/`, `docs/`, `testdata/` | Runtime/load/ops tooling; audits/runbooks; CSV fixtures |
| `perf-artifacts/`, `test-results/`, `tmp/` | Historical performance/test/debug evidence |
| `.github/workflows/`, `.vscode/` | Automation/editor configuration |
| `docker-compose.yml`, `Makefile`, `.env.example` | Local stack, convenience targets and template |

The supplied Git repository is at `C:\Project\AI-COO\AI-COO`; root commands run beside this README and Compose file.

## Technology

| Layer | Declared versions |
| --- | --- |
| Python | Docker/CI 3.12; no `requires-python` in pyproject |
| API/validation | FastAPI >=0.115, Uvicorn >=0.30, Pydantic >=2.8, settings >=2.4, email-validator >=2.2, multipart >=0.0.9 |
| Database | SQLAlchemy async >=2.0, Alembic >=1.13, asyncpg >=0.29, psycopg2 >=2.9 |
| Security | argon2-cffi >=23.1, python-jose[cryptography] >=3.3 |
| Tasks/cache | Celery[redis] >=5.4, Redis client >=5.0 |
| Adapters | boto3 >=1.34, ReportLab >=4.2, HTTPX >=0.27, Stripe >=11.6, Resend >=2.13 |
| Telemetry | structlog >=24.4, Sentry SDK >=2.13 |
| Backend dev | pytest >=8.3, asyncio >=0.24, cov >=5.0, Ruff >=0.6, Black >=24.8, mypy >=1.11 |
| Frontend | Node 20 Docker/CI, Next.js 15.5.12, React/DOM 18.3.1, TypeScript 5.6.2 |
| State/data | Query ^5.90.21, Table ^8.21.3, Virtual ^3.13.19, Zustand ^5.0.11, Zod ^4.3.6 |
| UI/charts | Tailwind ^3.4.17, Radix primitives, next-themes ^0.4.6, Lucide ^0.577.0, Framer Motion ^12.35.0, Recharts 2.13.0 |
| Frontend dev | Playwright ^1.58.2, ESLint 9.11.1, Next ESLint 15.5.12, Prettier ^3.8.1 |
| Containers | PostgreSQL 16, Redis 7, MinIO latest, Python 3.12-slim, Node 20-alpine |

Full declarations: [backend/pyproject.toml](backend/pyproject.toml), [frontend/package.json](frontend/package.json). Frontend has `package-lock.json`; backend lower bounds have no dedicated lockfile. Radix covers dialog/dropdown/label/select/slot/tabs/toast/tooltip; class variance authority/clsx/Tailwind merge compose styles. Autoprefixer/PostCSS and Prettier Tailwind plugin support CSS/formatting. The declared Tailwind PostCSS v4 package coexists with the main Tailwind v3 configuration; inspect active PostCSS before upgrades.

## Local setup

### Docker

Prerequisites: Git, Docker/Compose v2. Host development also needs Python 3.12/Node/npm; browser tests need Chromium, load tests k6, ops Bash/tools. GNU Make is optional.

Create `.env` only when an existing configuration need not be preserved:

```powershell
Copy-Item .env.example .env
```

Bash: `cp .env.example .env`. Edit placeholders including SECRET_KEY; container URLs use service hostnames. Start:

```bash
docker compose --env-file .env up --build -d
docker compose ps
docker compose logs --tail=100 backend worker beat frontend
```

| Service | Address | Behavior/persistence |
| --- | --- | --- |
| Frontend | http://localhost:3000 | Production Next build/start |
| Backend | http://localhost:8000 | Alembic upgrade before Uvicorn |
| Swagger | http://localhost:8000/docs | Interactive current API |
| ReDoc | http://localhost:8000/redoc | Contract viewer |
| OpenAPI | http://localhost:8000/openapi.json | Generated schema |
| Health | http://localhost:8000/api/v1/health | DB/Redis JSON checks |
| PostgreSQL | localhost:5432 | `pgdata` volume |
| Redis | localhost:6379 | No persistence volume |
| MinIO API/console | http://localhost:9000 / http://localhost:9001 | `miniodata` volume |
| Worker/Beat | No HTTP port | Consume/dispatch UTC jobs |

Health returns `ok`, `db`, `redis`, `auth_cookie_mode` and `env`; healthy database/cache checks have `ok=true`. Inspect JSON `ok`, since failed checks can return HTTP 200. Worker/Beat/MinIO/email/providers are not checked. PostgreSQL now has a `pg_isready` healthcheck (2-second interval, 5-second timeout, 30 retries, 5-second start period). Backend, worker and Beat wait for PostgreSQL `service_healthy`; Redis and MinIO dependencies require only `service_started`. This does not verify all application dependencies or successful migrations. `docker compose down` preserves named volumes. ENV_FILE selects service env-file separately from Compose interpolation `--env-file`; align both for alternate configurations.

### Host development

```bash
docker compose --env-file .env up -d postgres redis minio
python -m venv .venv
```

Activate PowerShell `.\.venv\Scripts\Activate.ps1` or Bash `source .venv/bin/activate`. Export backend configuration; host processes use localhost rather than Docker hostnames:

```powershell
$env:SECRET_KEY = '<development-secret>'
$env:DATABASE_URL = 'postgresql+asyncpg://ai_coo:ai_coo@localhost:5432/ai_coo'
$env:REDIS_URL = 'redis://localhost:6379/0'
$env:MINIO_ENDPOINT = 'localhost:9000'
$env:MINIO_PUBLIC_BASE_URL = 'http://localhost:9000'
$env:ENV = 'development'
Set-Location backend
python -m pip install -e '.[dev]'
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Settings loads `.env` relative to process cwd; starting from backend does not automatically load parent `.env`. Worker/Beat terminals use the same backend environment/cwd:

```bash
celery -A app.jobs.celery_app.celery_app worker --loglevel=INFO --concurrency=3 --prefetch-multiplier=1
celery -A app.jobs.celery_app.celery_app beat --loglevel=INFO
```

Use Linux worker containers on Windows. From frontend run `npm ci`, then `npm run dev`. Example frontend `.env.local`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_INTERNAL_API_URL=http://localhost:8000
NEXT_PUBLIC_AUTH_MODE=bearer
NEXT_PUBLIC_MINIO_PUBLIC_BASE_URL=http://localhost:9000
```

Frontend endpoint paths include /api/v1 so browser base excludes it; smoke/E2E base includes it. Internal backend hostname applies only inside Compose.

**Frontend build:** NEXT_PUBLIC variables are embedded by next build. Dockerfile builds before Compose applies runtime env_file and declares no public-variable build args. Custom URLs/cookie mode must reach the actual build environment; runtime restart alone is insufficient. Copied frontend env files can affect build; review the build context.

## Authentication and security

Memberships join users/orgs and routes enforce membership server-side. Isolation is application scoping, not a claim of database row-level security. OWNER administers organization/members/security/billing/sensitive operations; EDITOR mutates authorized data; VIEWER reads authorized data. Invitations accept MANAGER, memberships store roles as strings, and Workforce/UI policies recognize MANAGER for self/direct-report workflows. The older core `Role` enum still declares OWNER/EDITOR/VIEWER; authorization remains specific to each endpoint rather than universally granting MANAGER editor permissions. Exact restrictions are endpoint-specific: some member endpoints permit writes such as AI chat. UI visibility is not the security boundary.

Argon2id uses `time_cost=3`, `memory_cost=65536` and `parallelism=2`. JWT defaults are HS256, 15-minute access and 14-day refresh lifetimes. Refresh rotation, revocation, token-family reuse detection and audit events are implemented. Access authentication checks the user's active state. Session revocation primarily affects refresh behavior; already-issued access JWTs are not guaranteed to be immediately invalidated.

- Bearer default: response tokens persisted in browser localStorage, Authorization header.
- Cookie: HttpOnly auth cookies/token bodies omitted, credentials and double-submit CSRF on mutations. Align AUTH_COOKIE_MODE and build-time NEXT_PUBLIC_AUTH_MODE=cookie with matching cookie/header names.

Local cookie defaults secure=false/SameSite=lax. Configure HTTPS/origins/secure cookies deliberately. Backend tries bearer first even with cookie support.

MFA provides TOTP setup, enable/disable, and hashed single-use recovery codes with regeneration. Owner policy can require MFA, token-age limits and sensitive-action reauthentication. Obtain a scoped reauth token and send `X-Reauth-Token`. Policy age uses access JWT `iat`, rather than the absolute lifetime of a refreshed login family. Redis rate limiting defaults to 20 requests/minute; lockout defaults to six failures within 15 minutes, followed by a 30-minute lockout. Middleware handles request IDs, timing, HTTPS and CSRF; audits cover auth, business and operational actions.

PII Fernet keyring entries are `key-id:<valid-fernet-key>`. Empty keyring passes plaintext through. Coverage is selected fields rather than all columns. Preserve old keys for rotation; decrypt failure/unknown key returns stored value, so verify decryptability before reencrypting. Generate standard key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Development confirmation helper GET /api/v1/auth/dev/confirmation-token?email=... is ENV=development-only. Invite response token exposure defaults true; disable for production and configure delivery. See [secret hygiene](docs/operations/secret_hygiene_checklist.md) and [privacy](docs/operations/privacy_deletion.md).

## Confirmation and email delivery

Registration issues a confirmation link and a six-digit code, storing their hashes and invalidating previous unused confirmations. `FRONTEND_URL` defaults to `http://localhost:3000` and builds `/auth/confirm?token=...`. Link TTL defaults to 30 minutes, code TTL to 15 minutes and failed-code attempts to five. Confirm with a token or with email plus code; supplying a password for invitation acceptance requires a token. Successful confirmation consumes the token and activates the user. Resend returns a generic acknowledgment to avoid revealing whether an account exists or is already active.

`EMAIL_PROVIDER` accepts `smtp` (default) or `resend`. `EMAIL_DRY_RUN` bypasses real delivery and produces `sent_dry_run` results. SMTP supports `SMTP_SSL` or `SMTP_STARTTLS` and multipart plain/HTML bodies. Resend uses its SDK and requires `RESEND_API_KEY` plus `EMAIL_FROM_ADDRESS` when sending live. `EMAIL_FROM_NAME`, `EMAIL_FROM_ADDRESS` and `EMAIL_REPLY_TO` configure message identity; configure SMTP host/port/user/password for that provider. No mail server is included in Compose.

Delivery uses the durable `email.send` outbox with deduplication and retries. The adapter returns status, provider, message ID and error; the consumer records sent/dry-run/retrying/failed outcomes, including announcement delivery records. A queued request or a successful dry run does not establish inbox delivery. Keep frontend URLs reachable by recipients and run worker/Beat/outbox processing to send confirmations and announcements.

## Workforce and HR

Workforce routes are mounted under `/api/v1/workforce`: employees, departments, titles, shifts, attendance, corrections, leave, payroll, announcements, HR and intelligence. Appendix A lists every method and contract; appendices C/D describe all entities and schemas. The branch adds 73 registered routes and 21 persistent models relative to the earlier 112-route/43-model snapshot.

### Organization context and access

Workforce accepts organization context through the request and `X-Org-Id`. Invalid UUIDs return 422, conflicting header/request organizations return 403, and missing required context returns 422. The organization setting `workforce_org_context_canonical` controls whether the header is mandatory. Inspect the stored setting/default migration for existing organizations rather than assuming every organization has the same policy. The frontend attaches `X-Org-Id` from the selected organization on Workforce requests.

OWNER and EDITOR operate organization-wide Workforce data where the endpoint permits. VIEWER reads permitted data. MANAGER scope links the signed-in user to an employee by case-insensitive email and includes that employee plus direct reports through `manager_employee_id`; it is not recursive hierarchy traversal and uses bounded employee queries (up to 5,000 rows). Managers cannot create employees; payroll administration requires OWNER/EDITOR. Employee/payroll/payslip detail responses and applicable CSV exports redact compensation for VIEWER/MANAGER. However, the employee-update route accepts MANAGER and forwards submitted compensation fields to the service without a separate field-level compensation guard; response redaction does not prohibit those writes. Its employee-scope check occurs after service mutation and before commit. This is an implementation limitation to review rather than a guarantee that every sensitive field is protected.

Workforce intelligence dashboard/report endpoints require membership and return organization aggregates; they do not apply the same per-employee manager scope or compensation redaction. AI dashboard/report grounding also includes these aggregate values. Do not assume detail-level redaction removes payroll totals from every aggregate or AI response.

### Employees, structure and shifts

Employees have department/title, manager, optional location, contact identifiers, employment dates, contract/probation dates and compensation. Employment types are FULL_TIME, PART_TIME, CONTRACTOR and INTERN; statuses are ACTIVE, ON_LEAVE, OFFBOARDED and TERMINATED; salary types are SALARIED and HOURLY. Input normalization and validation cover names/emails, nonnegative money and ordered dates. Directory/detail/edit/deactivation workflows keep employee identity separate from organization user membership. Creating an employee does not automatically provision a login or membership.

Departments and job titles provide organization structure. Shifts define scheduled times and grace behavior and can be assigned to employees. Manager relationships provide direct-report scope; location relationships support employee filtering and announcement audiences.

### Attendance and corrections

Attendance supports clock-in/out, manual records, day views, monthly calendars and correction requests. Statuses are PRESENT, ABSENT, LATE, HALF_DAY, LEAVE, HOLIDAY, REMOTE and WEEKEND_OFF. Dates and clock operations use UTC. Clock-out requires a clock-in for the same UTC date; an overnight-shift rollover is not implemented.

Worked minutes are the floored difference between checkout and check-in. Lateness uses the assigned shift start and grace; the fallback grace is five minutes. A PRESENT record can become LATE. Overtime is `max(worked_minutes - 480, 0)` for PRESENT/LATE/REMOTE records, rather than a configurable per-shift overtime rule. Any clock-in without clock-out is flagged as missing checkout, including a still-open working day.

Corrections move from PENDING to APPROVED or REJECTED. Approval applies proposed values and recalculates attendance; records capture the decision. This is a correction workflow rather than a complete immutable punch-event ledger.

### Leave types, balances and decisions

Leave types define paid/unpaid, active and approval requirements. Balances track allocation, used and pending days per employee/type/year; available days are allocation minus used minus pending. Requests validate active employee/type, date order, positive supplied days, year boundaries and overlap with approved leave. The caller supplies requested days; there is no automatic business-day/holiday-calendar calculation.

Requests reserve pending days and may require approval or follow automatic approval. Decisions include APPROVED, REJECTED and CANCELLED. Approved leave consumes balance and writes LEAVE attendance for each inclusive calendar date, clearing punches and worked/overtime values. Cancellation of approved leave refunds used days and changes matching LEAVE attendance to ABSENT; it does not restore the previous punches. Balance transitions in automatic approval and pending cancellation require care: the current service's pending-reservation adjustments depend on status branches and should not be treated as an exhaustively verified leave-accounting system.

### Payroll periods, calculations and payslips

Create a DRAFT period with start/end dates, generate entries for active employees, review attendance/compensation snapshots and edit adjustments. Regeneration and adjustment changes are DRAFT-only. Approval locks entries; the period then moves to APPROVED and can be marked PAID. Approval/payment actions trigger deduplicated communication templates and notifications where configured. CSV export, payslip preview and PDF generation support review and distribution. Marking PAID records a business decision; it does not transfer funds.

For SALARIED employees, gross pay is base salary less an unpaid-leave deduction, floored at zero. Deduction uses approved unpaid leave overlapping the period and divides base salary by the period's inclusive calendar-day count, capped at the base salary and rounded to two decimal places.

For HOURLY employees, regular hours are `max(total_hours - overtime_hours, 0)`; gross is regular hours times hourly rate plus overtime hours times hourly rate times the overtime multiplier (default 1.5). Bonuses and reimbursements add to net; deductions and advances subtract. Net is not universally floored at zero. Entry generation is bounded to 5,000 employees. Calculations do not implement statutory tax withholding, jurisdictional labor compliance, benefits accounting or bank payment execution.

### Announcements, templates and delivery

Announcements support DRAFT/PUBLISHED/ARCHIVED states, priority, pinning, expiry, acknowledgment requirements and scheduled publication. Audiences are ORG_ALL, DEPARTMENT, LOCATION, TITLE and MANAGER_TEAM. Audience evaluation uses linked employee data; read and acknowledgment receipts are recorded separately from delivery outcomes.

Templates support substitution variables and automation mappings for PAYROLL_PERIOD_APPROVED, PAYROLL_PERIOD_PAID, LEAVE_REQUEST_APPROVED and LEAVE_REQUEST_REJECTED. Automation uses organization/action deduplication; failure is logged and handled as best effort rather than making successful payroll/leave decisions depend on email availability. Scheduled publication is dispatched every minute by a registered Workforce Celery task.

Announcement attachments allow PDF, PNG, JPEG and text with a 10 MiB limit. Objects use MinIO and expiring download URLs. Outbox-backed delivery records distinguish SENT_DRY_RUN, SENT, RETRYING and FAILED; dry-run state and provider acceptance are distinct from recipient acknowledgment.

### HR policies, documents and checklists

Policies have code/title/body/version, active and acknowledgment requirements; publishing advances the version. Acknowledgments store employee/user/time, but uniqueness is per policy/employee rather than per published version, so the schema is not a complete independent acknowledgment history for every version. The acknowledgment service checks active policy rather than universally requiring a published-state transition first.

HR documents attach to an employee or policy. Uploads allow PDF, PNG, JPEG and text with a 15 MiB limit, use the configured MinIO bucket and return seven-day presigned downloads; announcement attachment URLs also expire after seven days. Deactivation changes metadata rather than deleting the stored object. ONBOARDING/OFFBOARDING checklists track title/details/due dates and completion actor/time, with complete/reopen operations; they do not automatically provision or revoke every account/integration.

### Workforce intelligence and alerts

Dashboard intelligence includes employee counts, recorded attendance, missing checkout/lateness, pending leave, unpaid/due payroll, contract/probation dates and required-announcement acknowledgment signals. Reports cover attendance by person/day, leave, payroll, current department headcount and labor by payroll period, with JSON export. Dashboard queries are bounded; report ranges and aggregate definitions should be considered when interpreting totals.

Attendance counts represent recorded statuses, so PRESENT does not automatically include LATE/REMOTE and absence rates use recorded days rather than every scheduled employee-day. Pending leave is organization-wide. Payroll reports include whole periods overlapping the requested range rather than prorating each entry. Due payroll includes unpaid periods ending on or before seven days ahead, including overdue periods. Required-announcement signals identify published required announcements with zero acknowledgments; they do not establish that every audience member has acknowledged.

Workforce alert subkinds reuse the existing ANOMALY/PROFIT_LEAK/RUNWAY alert kinds. Signals include today's missing checkouts, at least three late records in 14 days, pending leave, due/unpaid payroll, at least 15% recorded absence over 14 days, at least 600 overtime minutes over 30 days, contracts ending within 30 days and required announcements with zero acknowledgments. Severity escalates at source-defined count/rate thresholds; candidate queries are bounded and organization-wide rather than location-scoped. Dashboard, reports and assistant integrate these values with the existing financial experience.

## Financial calculations

Money is Decimal/database numeric, often two-decimal formatting/string JSON. Cash is recorded-ledger approximation, not a complete bank/general ledger.

| Metric | Formula |
| --- | --- |
| Cash | Starting cash + lifetime revenue - lifetime expense, scoped where supported |
| Dashboard net | Revenue MTD - expenses MTD |
| Dashboard burn | max(0, expenses MTD - revenue MTD) |
| Normal runway burn | Mean of available months' max(0, expense - revenue) |
| Conservative burn | Mean of two largest burns when two months exist |
| Runway days | int(cash/burn*30), zero burn sentinel `9999` |
| Runway alert | Below org threshold, default 60 days |

Summary uses to_date's month; from_date does not turn MTD cards into interval totals. Aggregates may represent whole selected month. Cashflow/benchmarks have separate range logic; weekly report MTD cards are not seven-day totals. Available lookback rows are not full calendar history. Negative cash can yield negative runway.

Forecast averages up to six available monthly aggregates:

| Scenario | Revenue | Expense |
| --- | --- | --- |
| BASE | 1.00x | 1.00x |
| HIGH | 1.10x | 0.95x |
| LOW | 0.90x | 1.10x |

Bands = revenue prediction ± expense prediction*0.1, heuristic rather than calibrated confidence. No trained trend/seasonality model. Empty history produces zeros; existing rows reuse does not guarantee longer-horizon backfill. Overrides persist prediction/metadata. Recompute deletes/regenerates org forecasts and can lose overrides. Financial model is org-wide rather than location-modelled.

## Transactions and imports

Transactions contain org/location/date/amount/type/category/vendor/notes/actor/timestamps. CRUD/remap audit, maintain aggregates, invalidate reads and enqueue alert recalculation where implemented. List supports pagination/search/filters.

CSV: UTF8 BOM, size/header/mapping/type/amount/row checks, duplicate skipping/location resolution, history/errors, preview/commit and personal/shared profiles. Mapping is domain-field to CSV-column. Required date/amount/type/category; optional vendor/notes/location. INCOME→REVENUE, COST→EXPENSE; comma separators removed for amount parsing. Use schema-compatible ISO dates. Default cap 5 MiB / 5242880 bytes; align frontend/backend.

Select org/location/file/mapping, preview commit=false, inspect invalid/duplicates, then commit=true and inspect actual counts/history/errors. Parser/header failures can reject whole file while import validation reports row errors. Preview does not persist/reserve rows. Exact dedupe rules live in transaction service/repo/idempotency helpers.

Fixtures: [six-month demo](shared/demo/transactions_6months.csv), [sample](testdata/sample_transactions.csv), [full scenario](testdata/transactions_full_scenario.csv), [duplicates](testdata/transactions_with_duplicates.csv), [invalid](testdata/transactions_invalid_rows.csv).

Refresh headers: X-Alert-Recalc-Task-Id/Status/Queued. Alerts can lag writes until worker completes; UI surfaces queued state.

## Budgets, locations, inventory and alerts

Budgets normalize month/category/type. Create/update adds a version and clears earlier current state; history remains. Revenue/expense variance=actual-planned, percent=variance/planned*100 or null at zero. Unbudgeted actual categories appear with planned0; lines sort absolute variance. Positive expense/revenue variance has different business meaning. Budgets are org-wide; location variance compares scoped actuals to those budgets.

Locations belong to org; archive/reactivate preserves history. Supported transaction/financial/alert/report endpoints scope by location; benchmarks compare. Location is not a separate permission tier or universal filter.

Inventory items have uppercase SKU/name/location/active/cost/reorder. SKU checks scope by location. INBOUND/OUTBOUND require positive quantity, ADJUSTMENT nonzero signed quantity; deltas positive/negative/signed. Quantity precision three decimals / velocity four / cost two. POs track quantity/received/date/location/cost/ref/status OPEN/PARTIAL/RECEIVED/CANCELLED.

Forecast lookback/horizon default 30 days, each1–365. Daily velocity=outbound/lookback; endpoint persists velocity. Effective stock=on-hand + eligible inbound due by horizon. Cover=effective/velocity (clamp negative0, null with no velocity), stockout=today+ceil(cover). HIGH at <=14 days, MEDIUM at <=30 days, stock below the reorder point escalates to HIGH. Cost exposure over 30 days=velocity*30*unit cost. It combines horizon inbound rather than simulating arrivals. PO creation is separate from stock receipt; this is not full procurement/fulfillment.

Alerts include category anomaly/vendor concentration/misc growth/budget/inventory/additional profit leak. MAD threshold 3.5 / z-score 3.0 and configurable baseline/spike fallback. Defaults vendor 50%, misc 1.4x, anomaly 1.5x, budget 10%. Metadata records impact/location/evidence; severity/impact ordering. Status OPEN/DISMISSED; assignment/ack separate workflow metadata. Assignment validates membership/history audited. Calculated runway risk does not imply every warning is a stored alert row.

## Reports and background operations

Generation returns queued job/status or reuses existing report. Identity/key supports org/week/location. Worker makes ReportLab letter PDF, uploads MinIO, stores metadata, enqueues deduplicated active owner/editor emails. Download presigned URL expires after one hour; public origin rewrite must preserve signing/host validity.

The PDF contains week dates, cash and MTD KPIs, runway, three BASE forecast points, up to five alerts, executive highlights and confidence. It uses dollar formatting and a compact single-page layout with truncation. Currency conversion and a customizable report designer are not implemented.

Lifecycle PENDING/RUNNING/RETRYING/SUCCEEDED/FAILED stores payload/results/error/time/correlation. Retry/cancel supported where authorized; cancel is not rollback. Outbox claims/sent/retry/failed and dead-letter replay/dismiss exist. Dedupe does not guarantee exactly-once external delivery.

Runtime schedules in [celery_app.py](backend/app/jobs/celery_app.py), UTC:

| Schedule | Time | Task |
| --- | --- | --- |
| Reports | Monday 01:00 | generate_all_org_reports |
| Scheduled Workforce announcements | Every minute | publish_due_workforce_announcements |
| Outbox | Every minute | process_outbox |
| Deletion | Daily 02:30 | purge_deletion_requests |
| Banks | Every 30 minutes | sync_all_active_bank_connections |

Controls pause, resume and manually run supported schedules. The new Workforce scheduled-publish task processes a default batch of 50 with up to three retries; it does not consult the persisted schedule-pause controls, so those controls should not be assumed to pause this dispatcher. Use one Beat dispatcher unless scheduling is coordinated across replicas. The older `beat_schedule.py` has two entries and can overwrite the schedule if imported; Compose uses the configuration in `celery_app.py`.

Durable notifications support read and read-all actions. SSE emits summary/count snapshots every 10 seconds by default, with an allowed interval of 3–60 seconds. The frontend reconnects after five seconds, falls back after three failures and polls every 15 seconds. Streams can retain database sessions; account for pool capacity and proxy timeouts. The stream does not offer historical event replay.

## AI summaries and chat

AI_PROVIDER selects stub/openai/ollama_server (ollama alias). Stub needs no external AI. OpenAI HTTPX adapter uses configured key/base/model, default model string `gpt-4o-mini`. Ollama mode expects a custom gateway receiving prompt/optional model and x-api-key, returning aiText/response/text/output. A standard Ollama endpoint is not automatically this contract.

Summary structure: headline/highlights/risks/actions/confidence. Grounding checks KPI/alert/workforce numbers, metric/time and causal claims; workforce terminology and recursively collected report values are included in the allowed context. Disallowed examples include EBITDA/ARR/churn/YoY/unsupported because or due-to. Numeric tolerance=max(0.5,1% supplied). Provider/parse/grounding failures produce deterministic fallback metadata; Ollama can repair/normalize malformed output.

Chat persists org-scoped sessions/messages and fallback_used/grounding_violations. Each answer receives the submitted message, current KPIs/alerts and Workforce dashboard/report context; full persisted conversation history is not passed as memory by AIChatService.chat. Chat does not execute business-changing tools. Summary/chat consume AI-summary quota. Grounding is rule-based mitigation, not a guarantee against every misleading answer.

GET /api/v1/ai/health?org_id=<uuid>&live_check=true probes provider. Without probe, configured health does not prove generation success. See [AI runbook](docs/operations/ai_live_mode.md) and live verifier.

## Integrations, billing and quotas

Banks offer stub/Plaid link token, public-token exchange, accounts/connections, async sync/cursors/run history/revoke. Stub generates deterministic examples; Plaid requires client/secret/environment/products/country/webhook config. Sync tracks external identities/internal rows; Beat dispatches every 30 minutes.

Webhook helper checks **X-Plaid-Signature as HMAC-SHA256 hexadecimal digest of raw payload with PLAID_WEBHOOK_SECRET**. It does not implement public-key/JWT verification. Confirm actual provider/gateway transport compatibility before declaring production webhook readiness. Matching item events enqueue connection sync.

Stripe connections associate org/provider account. Stripe-Signature/webhook secret verifies payment ingestion; event/ledger models support dedupe/reconciliation against internal revenue over ranges. This is not complete payout/tax/general-ledger accounting.

Separate subscription billing service creates customers/checkout/portal and updates subscription status/metadata via webhooks. Manual settings exist. No universal price catalog; configure chosen prices/redirects. Billing label/status is separate from plan quotas; do not assume automatic quota mapping.

Default FREE monthly limits: 10,000 transactions / 20 reports / 500 AI summaries. UsageService.consume raises if projected usage exceeds quota; these are enforced limits, not passive counters. Consumption/persistence depend on call site; race tests cover creation/increments.

## API conventions and examples

Prefix /api/v1, UUID IDs, ISO dates, Decimal often string JSON. Org ID placement varies query/path/body. Runtime [Swagger](http://localhost:8000/docs)/[OpenAPI](http://localhost:8000/openapi.json) gives exact shapes; [shared export](shared/contracts/openapi/openapi.json) may lag code. Appendix lists registered routes/source signatures.

Error envelope:

```json
{"code":"validation_error","message":"Validation failed","request_id":"<id>","details":[],"detail":[]}
```

Detail supports older clients. Statuses commonly 400 (bad request), 401 (auth or reauth), 403 (role, tenant or policy), 404 (missing), 409 (conflict), 422 (validation), 429 (throttling) and 500 (server error). Request IDs correlate. Idempotency-Key and business dedupe apply to selected operations, not every POST.

Bash/curl examples (Windows use curl.exe/HTTP cmdlets; replace placeholders):

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"owner@example.com","password":"Password123!"}'
curl -X POST http://localhost:8000/api/v1/auth/confirm \
  -H 'Content-Type: application/json' -d '{"token":"<CONFIRM_TOKEN>"}'
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"owner@example.com","password":"Password123!"}'
curl -X POST http://localhost:8000/api/v1/organizations \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -H 'Content-Type: application/json' -d '{"name":"Acme LLC"}'
```

Preview, then repeat with commit=true:

```bash
curl -X POST http://localhost:8000/api/v1/transactions/import/csv \
  -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  -F 'org_id=<ORG_ID>' -F 'commit=false' \
  -F 'mapping={"date":"date","amount":"amount","type":"type","category":"category","vendor":"vendor","notes":"notes"}' \
  -F 'file=@shared/demo/transactions_6months.csv'
curl -X POST 'http://localhost:8000/api/v1/reports/generate?org_id=<ORG_ID>&week_start=2026-09-14' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>'
curl 'http://localhost:8000/api/v1/jobs?org_id=<ORG_ID>' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>'
```

Cookie clients preserve cookie jar/send CSRF cookie value in matching header for mutations. Cookie smoke/E2E exercises complete workflow.

## Frontend

| Canonical route | Purpose |
| --- | --- |
| / | Auth entry redirect |
| /auth/login | Login/MFA/recovery |
| /auth/register | Registration/invite acceptance |
| /auth/confirm | Confirmation/resend |
| /app | Protected entry |
| /app/dashboard | KPI/chart/variance/benchmark/alerts/summary |
| /app/transactions | CRUD/filter/table/CSV/profiles/history |
| /app/budgets | Budget versions/variance |
| /app/inventory | Items/stock/PO/risk |
| /app/forecast | Scenario/bands/overrides |
| /app/assistant | Chat sessions/messages |
| /app/alerts | Actions/assignment/history |
| /app/reports | Async PDF generation/progress/preview/download and workforce reports/JSON export |
| /app/settings | Financial/security/location/integration/billing/member/privacy |
| /app/activity | Operations overview, inventory and recent jobs/runtime activity |
| /app/admin-console | Advanced jobs/outbox/runtime/dead-letter/security administration |
| /app/workforce | Workforce overview/intelligence |
| /app/workforce/employees | Employee directory and creation |
| /app/workforce/employees/[employeeId] | Employee detail/editing |
| /app/workforce/attendance | Attendance, shifts and corrections |
| /app/workforce/leave | Types, balances and request decisions |
| /app/workforce/payroll | Periods, generation, adjustments, approval, payment records, exports and payslips |
| /app/workforce/communications | Announcements, audience, receipts, attachment/delivery state |
| /app/workforce/communications/templates | Templates and automation mappings |
| /app/workforce/hr | Policies, documents and onboarding/offboarding checklists |
| /app/onboarding | Readiness |
| /app/orgs | Org list/create |

Compatibility routes /login,/register,/confirm through (auth), plus /dashboard,/transactions,/forecast,/reports,/settings,/activity,/budgets,/onboarding. Parenthesized group names do not appear in URLs.

Primary navigation is Home, Money, Workforce, Forecast, Reports and AI COO; secondary navigation is Alerts, Operations and Settings. Admin Console visibility also depends on role and the simple/standard/advanced experience tier. A mobile drawer and collapsible desktop navigation share organization selection and preferences. Providers compose query/theme/global feedback/toasts; protected guard/layout bootstraps session. Shell adds navigation/org-location selectors/date range/breadcrumbs/command palette/notification/logout. CSS light/dark tokens, IBM Plex Sans/Space Grotesk and custom Recharts wrappers define UI.

API client manages transport/request IDs/refresh/errors/auth expiry/network feedback. Feature hooks mutate/invalidate/optimistically update queries; query keys/prefetch manage server state; Zustand selections; Zod/TypeScript contracts. Transactions virtualize/paginate. Feature workspaces now split containers, panels, hooks and service adapters across transactions, budgets, forecast, inventory, onboarding, organization, reports, assistant, alerts and Workforce. Settings is divided into financial/security/integration/billing/compliance/team/danger/Workforce panels, although its orchestration remains substantial. Shared layout/data-surface/state primitives provide responsive tables/cards, loading, empty, error/retry and permission states; dialogs constrain height and scroll.

Next config disables powered-by/enables compression/Lucide optimized imports/keeps TS-ESLint checks. Analyze script sets ANALYZE=true without active analyzer plugin wiring. [Handover](docs/frontend_current_state_handover.md)/[improvement plan](docs/frontend_complete_improvement_plan.md) describe current behavior/proposed work separately.

## Database and configuration

Models cover accounts/auth/confirmation, org/membership/settings/billing/quotas, transactions/import/profile/aggregate/forecast/alert/report, job/outbox/DLQ/schedule/notification/deletion, bank/payment, budget/location/inventory/chat, employees/departments/titles/shifts/attendance/corrections, leave types/balances/requests, payroll periods/entries/adjustments, announcement templates/audiences/receipts/attachments/deliveries, HR policies/acknowledgments/documents/checklists. Appendix lists all declared fields/contracts; inspect bases/mixins/constraints/migrations for actual inherited/storage behavior.

Monthly aggregates optimize reads; org/date/type/category/created indexes, open-alert partial index, transaction trigram search and PostgreSQL-specific/version-table-compatible migrations exist. SQLite is not the documented substitute.

```bash
python -m alembic upgrade head
python -m alembic current
python -m alembic history
```

Run from configured backend. Model changes need reviewed revisions. Safety checker upgrade/downgrade/re-upgrade uses a disposable DB because rollback removes schema/data. Appendix lists all 40 revisions, including Workforce revisions 0029–0039 and confirmation/provider revision 0040.

Required settings SECRET_KEY/DATABASE_URL/REDIS_URL. Appendix lists every alias/default and source-detected frontend/script/test variable. Template differs from code (role pool overrides unset in code/supplied in example). Groups include auth/runtime/PII, storage/cache/pools/workers, SMTP/Resend/confirmation, AI/Plaid/Stripe, SLO/Sentry, browser/internal URLs/SSE/CSV/Plaid UI and test/load/ops.

APP_ROLE is read directly by session setup; Compose uses api/worker/beat. ENV_FILE/POSTGRES_*/WORKER_CONCURRENCY/PREFETCH also control Compose. Do not publish private local env/performance-token values.

## Testing and CI

Backend with dev dependencies/environment:

```bash
python -m pytest app/tests -q
python -m ruff check app
python scripts/migration_safety_check.py
```

Most unit/API tests use fakes/overrides; live DB/provider tests are gated. Tests span auth/tenant/policy, data/import/financial, budgets/locations/inventory/alerts, AI/chat/grounding, reports/tasks/outbox/DLQ, quota/cache/pool races, integrations/errors/ops. Appendix lists files/tests.

Frontend:

```bash
npm ci
npm run check
npx playwright install chromium
npm run e2e
```

Playwright now starts the frontend unless `E2E_USE_EXTERNAL_BASE_URL=1`; the backend and its dependencies must already be running. Default `E2E_BASE_URL` is `http://localhost:3001`. Default `E2E_WEB_SERVER_MODE=start` runs a production build/start, cleaning `.next` first unless `E2E_CLEAN_NEXT_CACHE=0`; `dev` selects development mode. Existing-server reuse is disabled and startup timeout is 900,000 ms. Tests use Chromium, serial execution, one retry, a 180-second test timeout and 15-second expectation timeout; `E2E_WORKERS` defaults to one. Failure traces/screenshots/video are retained. Environment precedence is `.env.e2e.local`, `.env.local`, then parent `.env`, without overriding process values.

Global setup probes backend health and rejects a known mismatch between `E2E_AUTH_MODE` and `auth_cookie_mode`. `E2E_SKIP_AUTH_PREFLIGHT=1` disables this check; unavailable health or a missing mode field only warns, so preflight is not complete readiness validation. Align backend mode, compiled frontend mode and test mode for each lane.

Scripts include `e2e:full`, `e2e:smoke`, `e2e:smoke:ci`, `e2e:smoke:ci:full`, `e2e:workforce`, `e2e:workforce:ci`, `e2e:workforce:gate`, workforce responsive/RBAC/on-off/communications-failure/activity-failure/mobile-dense/states lanes, `e2e:payroll-workflow`, `e2e:leave-workflow`, plus headed/cookie/SSE/integration/visual commands. Appendix E lists every exact script. Cookie/SSE/visual/Plaid/live Stripe flags and credentials control relevant lanes; fixtures support disposable/seeded users and retries.

```bash
npm run e2e:workforce
npm run e2e:payroll-workflow
npm run e2e:leave-workflow
npm run e2e:workforce:gate
```

Root:

```bash
python scripts/smoke_mvp.py --base-url http://localhost:8000/api/v1 --auth-mode bearer
python scripts/smoke_mvp.py --base-url http://localhost:8000/api/v1 --auth-mode cookie
python scripts/verify_runtime.py --api-base-url http://localhost:8000/api/v1 --frontend-base-url http://localhost:3000
python scripts/ops/secret_hygiene_audit.py --root . --env-file .env.example
```

Verifier resolves root `.venv/Scripts/python.exe`, then `.venv/bin/python`, then the current `sys.executable`. It runs bearer first and adds cookie when process `AUTH_COOKIE_MODE` is enabled. It sets E2E external-server mode rather than starting or rebuilding the frontend. It does not switch backend authentication mode between lanes; the new preflight can reject the bearer lane against a cookie-mode backend. Use separately aligned runtime/test lanes where necessary. Options skip-backend-tests/skip-e2e/with-visual/health-timeout. Readiness checks HTTP 200, not JSON ok. Smoke/bootstrap can create users/org/data; use disposable environment.

Make has backend-test/lint/migration-safety/frontend-lint/build/precommit/smoke/verify-runtime/check/backup/restore-drill. Check only runs backend tests/frontend lint-build. Windows Python paths differ across targets; activated-env commands are clearer. Precommit Ruff v0.6.9.

[ci.yml](.github/workflows/ci.yml): migration/backend/frontend/precommit/secret gates and an unconditional `playwright-e2e-smoke` Compose lane, plus conditional integration/cookie/SSE/visual/Plaid/AI-live/Stripe. The unconditional lane runs frontend smoke, payroll-workflow and leave-workflow suites; the cookie lane also includes payroll/leave workflows. Available Workforce gate scripts do not imply that the full aggregate Workforce gate runs in every CI job. PR/main push/manual triggers. CI_E2E_COOKIE_LANE/SSE_LANE/VISUAL_LANE/PLAID_LANE and CI_AI_LIVE_MODE_LANE/manual controls. Stripe condition checks repository vars while values come from secrets; configure both appropriately. [Lane guide](docs/operations/ci_env_gated_lanes.md) explains setup.

[perf.yml](.github/workflows/perf.yml) bootstraps/seeds/tests/exports. Workflow existence does not prove optional execution.

**Historical evidence:** the March 26 [SRS matrix](docs/final_srs_delta_matrix.md) reports 221 passed and four skipped backend tests, a successful frontend build, Playwright results of 19 expected, zero unexpected and nine skipped, and a stored passing read/runtime performance gate. Earlier documents show smaller suites. The April 9–10 [product-completion report](docs/PHASE6_PRODUCT_COMPLETION.md) records 233 backend passes/four skips, lint/build success and a later verifier result of 31 Playwright passes/10 skips. The May 20 [Workforce final audit](docs/workforce_final_audit_report.md) records integrated Docker validation across Workforce modules, role/scoping and responsive flows; its conclusions apply to the documented gate scope and key negative cases. These are historical snapshots; this branch reevaluation does not claim fresh September application, provider or E2E passes.

## Performance and observability

Aggregates/indexes/pagination/five-second read caches/Celery optimize work. Keys include org/supported filters/location; invalidation scans prefixes. Cache failure falls back DB; task/lockout/health still need Redis. Bounded role pools account for API instances/worker processes/SSE. Default concurrency 3 / prefetch 1; Redis broker/results lack Compose persistence, and DB tracking does not reconstruct lost queues automatically.

Tools include bootstrap single/multi-org/deterministic seed/eight k6 profiles: smoke/many-org-dashboard/report-burst/mixed-churn/read-hotpaths/write-heavy/runtime-observability/inventory-churn. Seed accepts orgs/file/actor/months/rows/chunks/RNG and recomputes aggregates; use disposable data.

```bash
k6 run scripts/loadtest/k6-read-hotpaths.js \
  -e BASE_URL=http://localhost:8000/api/v1 \
  -e ACCESS_TOKEN='<ACCESS_TOKEN>' -e ORG_IDS_JSON='["<ORG_ID>"]' \
  -e FROM_DATE=2026-09-01 -e TO_DATE=2026-09-15 \
  -e RATE=13 -e RUNTIME_METRICS_ENABLED=false
```

Evaluator reads [guardrails](scripts/loadtest/slo_guardrails.json)/two read passes/runtime summary. Read gate requires both failures; runtime independent. Inventory collected but CLI does not accept a separate enforced inventory gate. Higher churn remains partial; enqueue latency differs from completion throughput.

Owner metrics, SLOs and diagnostics expose runtime evidence alongside request IDs, structlog and optional Sentry. SLO memory is process-local. Defaults are a 300-second window, a 2,000ms p95 threshold, a 1% server-error threshold and the top 20 endpoints. Queue lag defaults to a 180-second threshold. The [performance guide](docs/performance.md) details targets and profile context.

## Deployment and operations

Compose is local reference; Nginx is supplied but not a stack service. Config redirectsHTTPS/certificate mounts/routesAPI-front/security headers. Review SSE buffering/timeouts/report framing and restrict trusted proxy access: backend trusts forwarded headers from*. Docs/OpenAPI need separate proxy routes.

Generated bridge/base and desktop overlay contain namespace/deployments/services/expose/network-policy/PVC/local images and embedded development/credential config. Not a hardened production chart: replace embedded credentials with Secrets/review images-storage-readiness-network-replicas before deployment. Values are not reproduced here.

Runbooks cover [release](docs/operations/release_checklist.md), [owner/admin](docs/operations/owner_admin_runbook.md), [worker resilience](docs/operations/worker_resilience.md), [secrets](docs/operations/secret_hygiene_checklist.md) and [AI](docs/operations/ai_live_mode.md). Production configuration needs unique credentials, restricted CORS, HTTPS and secure cookies, verified SMTP/provider/webhook behavior, restricted token exposure, PII keys, capacity planning, backups and evidence from required gated checks.

The [backup runbook](docs/operations/backup_restore.md) targets a 24-hour RPO, two-hour RTO, daily backups and a weekly restore drill. These are objectives rather than measured guarantees. Bash scripts create PostgreSQL custom-format dumps and MinIO tar archives; manual compressed SQL examples use a different restore format. Select restore targets deliberately, preserve keyrings separately and verify database/object consistency. Redis is not backed up by these scripts; reconcile queues and outbox work after loss.

The [privacy runbook](docs/operations/privacy_deletion.md) covers deletion requests with a default 14-day grace period. Daily processing soft-deletes and redacts selected user, MFA, password, organization and billing fields and revokes sessions. Records, audits, transactions, chat, report objects and history remain; session metadata is not fully erased. The implemented purge is a redaction baseline rather than total storage erasure.

## Troubleshooting and limitations

| Symptom | Check |
| --- | --- |
| Settings/DB startup | Required env/cwd.env, host-vs-container URLs/readiness/migrations |
| Port conflict | 3000/8000/5432/6379/9000/9001 and matching config |
| Login/register | Confirmation/active/MFA/lockout;409existingemail |
| Network/cookie/policy | Compiled API/CORS/authmode/CSRF/security;MFA/tokenage/reauth |
| Queued jobs/stale alerts | Worker/broker/registration/schedules/job/cache |
| Report/email | MinIOobject/publicorigin/signature/expiry;dryrun;no bundled MailHog despite template hostname |
| AI/Plaid | Provider config/timeout/parse/grounding;rawHMAC/gatewaycompatibility |
| E2E/Make/verifier | Backend readiness, default frontend port 3001, build/start timeout, external-server flag, lane flags/seed/rate, backend/build/test auth alignment and interpreter resolution |
| Workforce 403/422 | Selected organization/X-Org-Id, canonical-context policy, employee email linkage, direct-report scope and endpoint role |
| Confirmation email/code | Worker/outbox, dry run/provider credentials/from address, frontend confirmation URL, expiry and attempt limit |
| Latency | Pool/concurrency/SSE/loadenvelope |
| Documentation mismatch | Current source/runtimeAPI versus older evidence |

Forecast/inventory/alerts are heuristics, not full ERP/accounting/multi-currency. Chat lacks full memory/tool execution; higher churn/optional lanes need deliberate verification. Compose gates PostgreSQL readiness but has no persistent Redis, bundled SMTP or HTTPS proxy; health does not verify all dependencies. Broad dependencies/unpinned MinIO affect reproducibility. Frontend build env/analyzer wiring/large pages/legacy aliases need care. PII defaults plaintext; deletion incomplete for related data. Generated manifests/alternate env/perf artifacts need hygiene; environment filenames and artifact payloads require care. `.env.cookie` is ignored by the current rules but is already staged in this workspace; documentation work preserves it and does not reproduce its contents. No LICENSE/support SLA/publication process was found; do not infer permissions from source availability.

Maintain changes across authorization/schemas/services/repos/migrations/frontend endpoint-types-query invalidation/tests/OpenAPI/runbooks. Preserve bearer-cookie/async/SSE behavior unless intentionally revising contracts.

## Complete implementation reference

Source-derived appendices inventory all tracked files and declared symbols. Signatures include dependencies; fields are code references, not write-access promises. Read bases/mixins/constraints/migrations for inherited/storage details. Secret values/artifact payloads are excluded.

- [A. API routes](#a-complete-api-route-reference)
- [B. Settings and environment variables](#b-complete-backend-settings)
- [C. Database models](#c-database-model-reference)
- [D. Request and response schemas](#d-request-and-response-schema-reference)
- [E. Commands and implementation symbols](#e-command-service-repository-adapter-and-task-reference)
- [F. Migration sequence](#f-migration-sequence)
- [G. Test inventory](#g-test-inventory)
- [H. Complete file catalog](#h-complete-file-catalog)
- [I. Research coverage](#i-research-coverage-and-verification-boundaries)

### A. Complete API route reference

Extracted recursively from registered routers, including all Workforce subrouters. Parameters preserve types, defaults and query/body/form/header bindings. Source guards include called local helper bodies; service-level and dynamic checks still require the linked implementation. A role literal is not by itself a grant of permission.

#### /api/v1/auth — [backend/app/api/v1/auth.py](backend/app/api/v1/auth.py)

- **POST /api/v1/auth/register** — `register`

  Parameters: `request: Request, response: Response, body: RegisterIn, db: AsyncSession=Depends(get_db)`

  Response model: `RegisterOut`

  Source guards: rate limiting

- **POST /api/v1/auth/login** — `login`

  Parameters: `request: Request, response: Response, body: LoginIn, db: AsyncSession=Depends(get_db)`

  Response model: `TokenOut`

  Source guards: rate limiting

- **POST /api/v1/auth/refresh** — `refresh`

  Parameters: `request: Request, response: Response, body: TokenRefreshIn, db: AsyncSession=Depends(get_db)`

  Response model: `TokenOut`

  Source guards: rate limiting

- **POST /api/v1/auth/invite/accept** — `accept_invite`

  Parameters: `request: Request, body: InviteAcceptIn, db: AsyncSession=Depends(get_db)`

  Response model: `RegisterOut`

  Source guards: rate limiting

- **POST /api/v1/auth/confirm** — `confirm`

  Parameters: `request: Request, body: ConfirmIn, db: AsyncSession=Depends(get_db)`

  Response model: `RegisterOut`

  Source guards: rate limiting

- **POST /api/v1/auth/resend-confirmation** — `resend_confirmation`

  Parameters: `request: Request, body: ResendConfirmationIn, db: AsyncSession=Depends(get_db)`

  Response model: `ResendConfirmationOut`

  Source guards: rate limiting

- **GET /api/v1/auth/dev/confirmation-token** — `dev_confirmation_token`

  Parameters: `email: str=Query(...), db: AsyncSession=Depends(get_db)`

  Response model: `DevConfirmationTokenOut`

  Source guards: No user/membership guard detected; inspect handler and transport validation.

- **POST /api/v1/auth/logout** — `logout`

  Parameters: `request: Request, response: Response, body: LogoutIn | None=None, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user

- **GET /api/v1/auth/me** — `me`

  Parameters: `user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `MeOut`

  Source guards: authenticated user

- **GET /api/v1/auth/mfa/status** — `mfa_status`

  Parameters: `user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `MfaStatusOut`

  Source guards: authenticated user

- **POST /api/v1/auth/mfa/setup** — `mfa_setup`

  Parameters: `request: Request, body: MfaSetupIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `MfaSetupOut`

  Source guards: authenticated user, rate limiting

- **POST /api/v1/auth/mfa/enable** — `mfa_enable`

  Parameters: `request: Request, body: MfaEnableIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `MfaRecoveryCodesOut`

  Source guards: authenticated user, rate limiting

- **POST /api/v1/auth/mfa/disable** — `mfa_disable`

  Parameters: `request: Request, body: MfaDisableIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, rate limiting

- **POST /api/v1/auth/mfa/recovery-codes/regenerate** — `mfa_regenerate_recovery_codes`

  Parameters: `request: Request, body: MfaRecoveryCodesRegenerateIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `MfaRecoveryCodesOut`

  Source guards: authenticated user, rate limiting

- **GET /api/v1/auth/sessions** — `list_sessions`

  Parameters: `request: Request, refresh_token: str | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `SessionListOut`

  Source guards: authenticated user

- **DELETE /api/v1/auth/sessions/{session_id}** — `revoke_session`

  Parameters: `session_id: uuid.UUID, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user

- **POST /api/v1/auth/sessions/revoke-others** — `revoke_other_sessions`

  Parameters: `request: Request, body: RevokeOthersIn=Body(default_factory=RevokeOthersIn), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user

- **POST /api/v1/auth/reauth** — `reauth`

  Parameters: `request: Request, body: ReauthIn, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `ReauthOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches, rate limiting

- **POST /api/v1/auth/delete-account** — `request_account_deletion`

  Parameters: `body: AccountDeletionRequestIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `DeletionRequestOut`

  Source guards: authenticated user

- **GET /api/v1/auth/delete-account/requests** — `list_account_deletion_requests`

  Parameters: `limit: int=Query(default=20, ge=1, le=100), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `DeletionRequestListOut`

  Source guards: authenticated user

#### /api/v1/organizations — [backend/app/api/v1/organizations.py](backend/app/api/v1/organizations.py)

- **POST /api/v1/organizations** — `create_org`

  Parameters: `body: OrganizationCreateIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `OrganizationOut`

  Source guards: authenticated user

- **GET /api/v1/organizations** — `list_orgs`

  Parameters: `user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[OrganizationOut]`

  Source guards: authenticated user

- **POST /api/v1/organizations/{org_id}/invite** — `invite`

  Parameters: `org_id: uuid.UUID, body: InviteIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, sensitive reauthentication, role dependency, role literals: OWNER; inspect allow/deny branches

- **GET /api/v1/organizations/{org_id}/members** — `members`

  Parameters: `org_id: uuid.UUID, _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `list[MemberOut]`

  Source guards: role dependency, role literals: OWNER; inspect allow/deny branches

- **GET /api/v1/organizations/{org_id}/settings** — `get_settings`

  Parameters: `org_id: uuid.UUID, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `OrgSettingsOut`

  Source guards: authenticated user, organization membership/policy

- **PUT /api/v1/organizations/{org_id}/settings** — `update_settings`

  Parameters: `org_id: uuid.UUID, body: OrgSettingsUpdateIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), ctx=Depends(get_org_context), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db)`

  Response model: `OrgSettingsOut`

  Source guards: authenticated user, organization membership/policy, sensitive reauthentication, role dependency, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/organizations/{org_id}/plan-usage** — `get_plan_usage`

  Parameters: `org_id: uuid.UUID, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `PlanUsageOut`

  Source guards: authenticated user, organization membership/policy

- **GET /api/v1/organizations/{org_id}/billing** — `get_billing`

  Parameters: `org_id: uuid.UUID, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `OrgBillingOut`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **PUT /api/v1/organizations/{org_id}/billing** — `update_billing`

  Parameters: `org_id: uuid.UUID, body: OrgBillingUpdateIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db)`

  Response model: `OrgBillingOut`

  Source guards: authenticated user, organization membership/policy, sensitive reauthentication, role dependency, role literals: OWNER; inspect allow/deny branches

- **POST /api/v1/organizations/{org_id}/billing/checkout** — `create_billing_checkout`

  Parameters: `org_id: uuid.UUID, body: BillingCheckoutIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db)`

  Response model: `BillingCheckoutOut`

  Source guards: authenticated user, organization membership/policy, sensitive reauthentication, role dependency, role literals: OWNER; inspect allow/deny branches

- **POST /api/v1/organizations/{org_id}/billing/portal** — `create_billing_portal`

  Parameters: `org_id: uuid.UUID, body: BillingPortalIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db)`

  Response model: `BillingPortalOut`

  Source guards: authenticated user, organization membership/policy, sensitive reauthentication, role dependency, role literals: OWNER; inspect allow/deny branches

- **POST /api/v1/organizations/billing/webhook** — `billing_webhook`

  Parameters: `request: Request, db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: webhook signature

- **POST /api/v1/organizations/{org_id}/delete** — `request_org_deletion`

  Parameters: `org_id: uuid.UUID, body: OrgDeletionRequestIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db)`

  Response model: `DeletionRequestOut`

  Source guards: authenticated user, organization membership/policy, sensitive reauthentication, role dependency, role literals: OWNER; inspect allow/deny branches

#### /api/v1/locations — [backend/app/api/v1/locations.py](backend/app/api/v1/locations.py)

- **GET /api/v1/locations** — `list_locations`

  Parameters: `org_id: uuid.UUID=Query(...), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[LocationOut]`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/locations** — `create_location`

  Parameters: `body: LocationCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `LocationOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **PUT /api/v1/locations/{location_id}** — `update_location`

  Parameters: `location_id: uuid.UUID, body: LocationUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `LocationOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **DELETE /api/v1/locations/{location_id}** — `delete_location`

  Parameters: `location_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

#### /api/v1/transactions — [backend/app/api/v1/transactions.py](backend/app/api/v1/transactions.py)

- **POST /api/v1/transactions** — `create_tx`

  Parameters: `request: Request, response: Response, body: TransactionCreateIn, idempotency_key: str | None=Header(default=None, alias='Idempotency-Key'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `dict`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/transactions** — `list_tx`

  Parameters: `org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), from_date: str | None=Query(None, alias='from'), to_date: str | None=Query(None, alias='to'), type: str | None=None, category: str | None=None, q: str | None=None, page: int=1, page_size: int=20, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `TransactionPageOut`

  Source guards: authenticated user, organization membership/policy

- **PUT /api/v1/transactions/{tx_id}** — `update_tx`

  Parameters: `request: Request, response: Response, tx_id: uuid.UUID, body: TransactionUpdateIn, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db)`

  Response model: `dict`

  Source guards: authenticated user, role dependency, role literals: EDITOR, OWNER; inspect allow/deny branches

- **DELETE /api/v1/transactions/{tx_id}** — `delete_tx`

  Parameters: `request: Request, response: Response, tx_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, role dependency, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/transactions/import/csv** — `import_csv`

  Parameters: `request: Request, response: Response, org_id: uuid.UUID=Form(...), mapping: str | None=Form(None), profile_id: uuid.UUID | None=Form(None), commit: bool=Form(True), file: UploadFile=File(...), idempotency_key: str | None=Header(default=None, alias='Idempotency-Key'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `CSVImportOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/transactions/imports** — `list_imports`

  Parameters: `org_id: uuid.UUID=Query(...), page: int=1, page_size: int=20, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `ImportHistoryPageOut`

  Source guards: authenticated user, organization membership/policy

- **GET /api/v1/transactions/imports/{import_id}/errors** — `download_import_errors`

  Parameters: `import_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/transactions/bulk/remap-category** — `bulk_remap_category`

  Parameters: `request: Request, response: Response, body: BulkCategoryRemapIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/transactions/import-profiles** — `list_import_profiles`

  Parameters: `org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[ImportMappingProfileOut]`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/transactions/import-profiles** — `create_import_profile`

  Parameters: `body: ImportMappingProfileIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `ImportMappingProfileOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **PUT /api/v1/transactions/import-profiles/{profile_id}** — `update_import_profile`

  Parameters: `profile_id: uuid.UUID, body: ImportMappingProfileUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `ImportMappingProfileOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **DELETE /api/v1/transactions/import-profiles/{profile_id}** — `delete_import_profile`

  Parameters: `profile_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

#### /api/v1/budgets — [backend/app/api/v1/budgets.py](backend/app/api/v1/budgets.py)

- **GET /api/v1/budgets** — `list_budgets`

  Parameters: `org_id: uuid.UUID=Query(...), period: str | None=Query(default=None, description='Month as YYYY-MM or first day YYYY-MM-DD (normalized to month start).'), budget_type: str | None=Query(default=None), include_history: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[BudgetOut]`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/budgets** — `create_budget`

  Parameters: `request: Request, response: Response, body: BudgetCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `BudgetOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **PUT /api/v1/budgets/{budget_id}** — `update_budget`

  Parameters: `request: Request, response: Response, budget_id: uuid.UUID, body: BudgetUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `BudgetOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

#### /api/v1/analytics — [backend/app/api/v1/analytics.py](backend/app/api/v1/analytics.py)

- **GET /api/v1/analytics/summary** — `summary`

  Parameters: `org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), from_date: date=Query(..., alias='from'), to_date: date=Query(..., alias='to'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `SummaryOut`

  Source guards: authenticated user, organization membership/policy

- **GET /api/v1/analytics/cashflow** — `cashflow`

  Parameters: `org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), from_date: date=Query(..., alias='from'), to_date: date=Query(..., alias='to'), granularity: str='month', user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `CashflowOut`

  Source guards: authenticated user, organization membership/policy

- **GET /api/v1/analytics/budget-variance** — `budget_variance`

  Parameters: `org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), period: str | None=Query(default=None, description='Month as YYYY-MM or YYYY-MM-DD (normalized to month start). Defaults to current month.'), budget_type: str | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `BudgetVarianceOut`

  Source guards: authenticated user, organization membership/policy

- **GET /api/v1/analytics/location-benchmark** — `location_benchmark`

  Parameters: `org_id: uuid.UUID=Query(...), from_date: date=Query(..., alias='from'), to_date: date=Query(..., alias='to'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `LocationBenchmarkOut`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/analytics/recompute** — `recompute`

  Parameters: `request: Request, org_id: uuid.UUID=Query(...), idempotency_key: str | None=Header(default=None, alias='Idempotency-Key'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `AnalyticsRecomputeOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

#### /api/v1 — [backend/app/api/v1/runway.py](backend/app/api/v1/runway.py)

- **GET /api/v1/runway** — `runway`

  Parameters: `org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), lookback_months: int=6, conservative: bool=False, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `RunwayOut`

  Source guards: authenticated user, organization membership/policy

#### /api/v1/forecast — [backend/app/api/v1/forecast.py](backend/app/api/v1/forecast.py)

- **GET /api/v1/forecast** — `get_forecast`

  Parameters: `org_id: uuid.UUID=Query(...), months: int=3, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `ForecastOut`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/forecast/override** — `override_forecast`

  Parameters: `body: ForecastOverrideIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

#### /api/v1/alerts — [backend/app/api/v1/alerts.py](backend/app/api/v1/alerts.py)

- **GET /api/v1/alerts** — `list_alerts`

  Parameters: `org_id: uuid.UUID=Query(...), status: str | None=Query(default=None), assignee_user_id: uuid.UUID | None=Query(default=None), location_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `AlertsOut`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/alerts/{alert_id}/dismiss** — `dismiss_alert`

  Parameters: `alert_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/alerts/{alert_id}/assign** — `assign_alert`

  Parameters: `alert_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), assignee_user_id: uuid.UUID | None=Query(default=None), body: dict[str, Any] | None=Body(default=None), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db)`

  Response model: `dict`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/alerts/{alert_id}/acknowledge** — `acknowledge_alert`

  Parameters: `alert_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), body: dict[str, Any] | None=Body(default=None), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db)`

  Response model: `dict`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/alerts/{alert_id}/history** — `alert_history`

  Parameters: `alert_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `AlertHistoryOut`

  Source guards: authenticated user, organization membership/policy

#### /api/v1/reports — [backend/app/api/v1/reports.py](backend/app/api/v1/reports.py)

- **GET /api/v1/reports** — `list_reports`

  Parameters: `org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `ReportsOut`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/reports/generate** — `generate`

  Parameters: `request: Request, org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), week_start: date=Query(...), idempotency_key: str | None=Header(default=None, alias='Idempotency-Key'), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db)`

  Response model: `ReportGenerateOut`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/reports/{report_id}/download** — `download`

  Parameters: `report_id: uuid.UUID, org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy

#### /api/v1/jobs — [backend/app/api/v1/jobs.py](backend/app/api/v1/jobs.py)

- **GET /api/v1/jobs** — `list_jobs`

  Parameters: `org_id: uuid.UUID=Query(...), status: str | None=None, task_name: str | None=None, since: datetime | None=None, until: datetime | None=None, page: int=1, page_size: int=20, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `JobPageOut`

  Source guards: authenticated user, organization membership/policy, role literals: VIEWER; inspect allow/deny branches, role-based response redaction

- **POST /api/v1/jobs/{job_id}/cancel** — `cancel_job`

  Parameters: `job_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `JobCommandResult`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/jobs/{job_id}/retry** — `retry_job`

  Parameters: `job_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `JobCommandResult`

  Source guards: authenticated user, organization membership/policy

#### /api/v1/admin — [backend/app/api/v1/admin.py](backend/app/api/v1/admin.py)

- **POST /api/v1/admin/recompute** — `recompute_all`

  Parameters: `request: Request, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **GET /api/v1/admin/outbox** — `list_outbox`

  Parameters: `org_id: uuid.UUID=Query(...), status: str | None=None, event_type: str | None=None, page: int=1, page_size: int=20, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `OutboxPageOut`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **POST /api/v1/admin/outbox/{event_id}/retry** — `retry_outbox_event`

  Parameters: `event_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **GET /api/v1/admin/system-status** — `system_status`

  Parameters: `org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `SystemStatusOut`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **GET /api/v1/admin/runtime-metrics** — `runtime_metrics`

  Parameters: `org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `RuntimeMetricsOut`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **GET /api/v1/admin/runtime-slos** — `runtime_slos`

  Parameters: `org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `RuntimeSLOOut`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **POST /api/v1/admin/schedules/{name}/pause** — `pause_schedule`

  Parameters: `name: str, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **POST /api/v1/admin/schedules/{name}/resume** — `resume_schedule`

  Parameters: `name: str, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **POST /api/v1/admin/schedules/{name}/run** — `run_schedule_now`

  Parameters: `name: str, request: Request, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **GET /api/v1/admin/audit/export** — `export_audit_logs`

  Parameters: `org_id: uuid.UUID=Query(...), since: datetime | None=Query(default=None), until: datetime | None=Query(default=None), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **POST /api/v1/admin/security/rotate-pii** — `rotate_org_pii`

  Parameters: `org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **GET /api/v1/admin/deletion-requests** — `list_deletion_requests`

  Parameters: `org_id: uuid.UUID=Query(...), limit: int=Query(default=50, ge=1, le=200), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `DeletionRequestListOut`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **GET /api/v1/admin/dead-letter** — `list_dead_letter`

  Parameters: `org_id: uuid.UUID=Query(...), status: str | None=None, source_type: str | None=None, page: int=Query(default=1, ge=1), page_size: int=Query(default=20, ge=1, le=100), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `DeadLetterPageOut`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **POST /api/v1/admin/dead-letter/{dead_letter_id}/replay** — `replay_dead_letter`

  Parameters: `dead_letter_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

- **POST /api/v1/admin/dead-letter/{dead_letter_id}/dismiss** — `dismiss_dead_letter`

  Parameters: `dead_letter_id: uuid.UUID, org_id: uuid.UUID=Query(...), reason: str | None=Query(default=None), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: OWNER; inspect allow/deny branches

#### /api/v1/ai — [backend/app/api/v1/ai.py](backend/app/api/v1/ai.py)

- **GET /api/v1/ai/health** — `ai_health`

  Parameters: `org_id: uuid.UUID=Query(...), live_check: bool=Query(default=False), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db)`

  Response model: `AIHealthOut`

  Source guards: authenticated user, organization membership/policy, role dependency, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/ai/summary** — `ai_summary`

  Parameters: `body: AISummaryRequest, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `AISummaryOut`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/ai/chat/sessions** — `create_ai_chat_session`

  Parameters: `body: AIChatSessionCreateIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `AIChatSessionOut`

  Source guards: authenticated user, organization membership/policy

- **GET /api/v1/ai/chat/sessions** — `list_ai_chat_sessions`

  Parameters: `org_id: uuid.UUID=Query(...), mine_only: bool=Query(default=False), limit: int=Query(default=50, ge=1, le=100), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[AIChatSessionOut]`

  Source guards: authenticated user, organization membership/policy

- **GET /api/v1/ai/chat/sessions/{session_id}** — `get_ai_chat_session`

  Parameters: `session_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `AIChatSessionDetailOut`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/ai/chat** — `ai_chat`

  Parameters: `body: AIChatRequest, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `AIChatOut`

  Source guards: authenticated user, organization membership/policy

#### /api/v1 — [backend/app/api/v1/health.py](backend/app/api/v1/health.py)

- **GET /api/v1/health** — `health`

  Parameters: `db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: No user/membership guard detected; inspect handler and transport validation.

#### /api/v1/events — [backend/app/api/v1/events.py](backend/app/api/v1/events.py)

- **GET /api/v1/events/stream** — `stream_updates`

  Parameters: `org_id: uuid.UUID=Query(...), interval_seconds: int=Query(default=10, ge=3, le=60), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy

#### /api/v1/notifications — [backend/app/api/v1/notifications.py](backend/app/api/v1/notifications.py)

- **GET /api/v1/notifications** — `list_notifications`

  Parameters: `org_id: uuid.UUID=Query(...), unread_only: bool=False, page: int=1, page_size: int=20, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `NotificationPageOut`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/notifications/{notification_id}/read** — `mark_read`

  Parameters: `notification_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/notifications/read-all** — `mark_all_read`

  Parameters: `org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy

#### /api/v1/integrations — [backend/app/api/v1/integrations.py](backend/app/api/v1/integrations.py)

- **POST /api/v1/integrations/banks/plaid/link-token** — `create_plaid_link_token`

  Parameters: `body: PlaidLinkTokenIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `PlaidLinkTokenOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/integrations/banks/plaid/exchange** — `exchange_plaid_public_token`

  Parameters: `body: PlaidExchangeIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `PlaidExchangeOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/integrations/banks/connections** — `list_bank_connections`

  Parameters: `org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[BankConnectionOut]`

  Source guards: authenticated user, organization membership/policy

- **DELETE /api/v1/integrations/banks/{connection_id}** — `revoke_bank_connection`

  Parameters: `connection_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/integrations/banks/{connection_id}/sync** — `enqueue_bank_sync`

  Parameters: `request: Request, connection_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `BankSyncEnqueueOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/integrations/banks/plaid/webhook** — `plaid_webhook`

  Parameters: `request: Request, plaid_signature: str | None=Header(default=None, alias='X-Plaid-Signature'), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: webhook signature

- **POST /api/v1/integrations/payments/stripe/connect** — `connect_stripe`

  Parameters: `body: StripeConnectIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `StripeConnectOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/integrations/payments/connections** — `list_payment_connections`

  Parameters: `org_id: uuid.UUID=Query(...), provider: str=Query(default='STRIPE'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[PaymentConnectionOut]`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/integrations/payments/stripe/webhook** — `stripe_webhook`

  Parameters: `request: Request, stripe_signature: str | None=Header(default=None, alias='Stripe-Signature'), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: webhook signature

- **GET /api/v1/integrations/payments/reconciliation** — `get_payment_reconciliation`

  Parameters: `org_id: uuid.UUID=Query(...), provider: str=Query(default='STRIPE'), date_from: date | None=Query(default=None), date_to: date | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `PaymentReconciliationOut`

  Source guards: authenticated user, organization membership/policy

#### /api/v1/inventory — [backend/app/api/v1/inventory.py](backend/app/api/v1/inventory.py)

- **GET /api/v1/inventory/items** — `list_items`

  Parameters: `org_id: uuid.UUID=Query(...), include_inactive: bool=Query(default=False), location_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[InventoryItemOut]`

  Source guards: authenticated user, organization membership/policy

- **POST /api/v1/inventory/items** — `create_item`

  Parameters: `request: Request, response: Response, body: InventoryItemCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `InventoryItemOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/inventory/stock-events** — `create_stock_event`

  Parameters: `request: Request, response: Response, body: InventoryStockEventCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `InventoryStockEventOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/inventory/purchase-orders** — `create_purchase_order`

  Parameters: `request: Request, response: Response, body: InventoryPurchaseOrderCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `InventoryPurchaseOrderOut`

  Source guards: authenticated user, organization membership/policy, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/inventory/forecast** — `get_forecast`

  Parameters: `org_id: uuid.UUID=Query(...), lookback_days: int=Query(default=30), horizon_days: int=Query(default=30), location_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `InventoryForecastOut`

  Source guards: authenticated user, organization membership/policy

#### /api/v1/workforce/employees — [backend/app/api/v1/workforce/employees.py](backend/app/api/v1/workforce/employees.py)

- **GET /api/v1/workforce/employees** — `list_employees`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), q: str | None=Query(default=None), department_id: uuid.UUID | None=Query(default=None), title_id: uuid.UUID | None=Query(default=None), manager_employee_id: uuid.UUID | None=Query(default=None), employment_status: str | None=Query(default=None), include_inactive: bool=Query(default=False), limit: int=Query(default=200, ge=1, le=5000), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceEmployeeOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, OWNER; inspect allow/deny branches, role-based response redaction

- **GET /api/v1/workforce/employees/{employee_id}** — `get_employee`

  Parameters: `request: Request, employee_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceEmployeeOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, OWNER; inspect allow/deny branches, role-based response redaction

- **POST /api/v1/workforce/employees** — `create_employee`

  Parameters: `request: Request, body: WorkforceEmployeeCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceEmployeeOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches, role-based response redaction

- **PUT /api/v1/workforce/employees/{employee_id}** — `update_employee`

  Parameters: `request: Request, employee_id: uuid.UUID, body: WorkforceEmployeeUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceEmployeeOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches, role-based response redaction

- **DELETE /api/v1/workforce/employees/{employee_id}** — `delete_employee`

  Parameters: `request: Request, employee_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: OWNER; inspect allow/deny branches

#### /api/v1/workforce/departments — [backend/app/api/v1/workforce/departments.py](backend/app/api/v1/workforce/departments.py)

- **GET /api/v1/workforce/departments** — `list_departments`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceDepartmentOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/departments** — `create_department`

  Parameters: `request: Request, body: WorkforceDepartmentCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceDepartmentOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **PUT /api/v1/workforce/departments/{department_id}** — `update_department`

  Parameters: `request: Request, department_id: uuid.UUID, body: WorkforceDepartmentUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceDepartmentOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **DELETE /api/v1/workforce/departments/{department_id}** — `delete_department`

  Parameters: `request: Request, department_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: EDITOR, OWNER; inspect allow/deny branches

#### /api/v1/workforce/titles — [backend/app/api/v1/workforce/titles.py](backend/app/api/v1/workforce/titles.py)

- **GET /api/v1/workforce/titles** — `list_titles`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceTitleOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/titles** — `create_title`

  Parameters: `request: Request, body: WorkforceTitleCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceTitleOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **PUT /api/v1/workforce/titles/{title_id}** — `update_title`

  Parameters: `request: Request, title_id: uuid.UUID, body: WorkforceTitleUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceTitleOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **DELETE /api/v1/workforce/titles/{title_id}** — `delete_title`

  Parameters: `request: Request, title_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: EDITOR, OWNER; inspect allow/deny branches

#### /api/v1/workforce/shifts — [backend/app/api/v1/workforce/shifts.py](backend/app/api/v1/workforce/shifts.py)

- **GET /api/v1/workforce/shifts** — `list_shifts`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceShiftOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/shifts** — `create_shift`

  Parameters: `request: Request, body: WorkforceShiftCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceShiftOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **PUT /api/v1/workforce/shifts/{shift_id}** — `update_shift`

  Parameters: `request: Request, shift_id: uuid.UUID, body: WorkforceShiftUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceShiftOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **DELETE /api/v1/workforce/shifts/{shift_id}** — `delete_shift`

  Parameters: `request: Request, shift_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/shifts/assignments** — `list_assignments`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), shift_id: uuid.UUID | None=Query(default=None), as_of: date | None=Query(default=None), limit: int=Query(default=200, ge=1, le=500), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceShiftAssignmentOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/shifts/assignments** — `create_assignment`

  Parameters: `request: Request, body: WorkforceShiftAssignmentCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceShiftAssignmentOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

#### /api/v1/workforce/attendance — [backend/app/api/v1/workforce/attendance.py](backend/app/api/v1/workforce/attendance.py)

- **GET /api/v1/workforce/attendance/daily** — `daily`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), date_value: date=Query(..., alias='date'), employee_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAttendanceDailyOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope

- **GET /api/v1/workforce/attendance/calendar** — `calendar`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), month: str=Query(..., description='Month in YYYY-MM'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAttendanceCalendarOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/attendance/clock-in** — `clock_in`

  Parameters: `request: Request, body: WorkforceAttendanceClockInIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAttendanceOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/attendance/clock-out** — `clock_out`

  Parameters: `request: Request, body: WorkforceAttendanceClockOutIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAttendanceOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/attendance/manual** — `manual`

  Parameters: `request: Request, body: WorkforceAttendanceManualIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAttendanceOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches

#### /api/v1/workforce/corrections — [backend/app/api/v1/workforce/corrections.py](backend/app/api/v1/workforce/corrections.py)

- **GET /api/v1/workforce/corrections** — `list_corrections`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), status: str | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), limit: int=Query(default=200, ge=1, le=500), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceAttendanceCorrectionOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope

- **POST /api/v1/workforce/corrections** — `request_correction`

  Parameters: `request: Request, body: WorkforceAttendanceCorrectionRequestIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAttendanceCorrectionOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/corrections/{correction_id}/review** — `review_correction`

  Parameters: `request: Request, correction_id: uuid.UUID, body: WorkforceAttendanceCorrectionReviewIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAttendanceCorrectionOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches

#### /api/v1/workforce/leave — [backend/app/api/v1/workforce/leave.py](backend/app/api/v1/workforce/leave.py)

- **GET /api/v1/workforce/leave/types** — `list_leave_types`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceLeaveTypeOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/leave/types** — `create_leave_type`

  Parameters: `request: Request, body: WorkforceLeaveTypeCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceLeaveTypeOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches

- **PUT /api/v1/workforce/leave/types/{leave_type_id}** — `update_leave_type`

  Parameters: `request: Request, leave_type_id: uuid.UUID, body: WorkforceLeaveTypeUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceLeaveTypeOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches

- **DELETE /api/v1/workforce/leave/types/{leave_type_id}** — `delete_leave_type`

  Parameters: `request: Request, leave_type_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/leave/balances** — `list_balances`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), year: int | None=Query(default=None), limit: int=Query(default=2000, ge=1, le=5000), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceLeaveBalanceOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope

- **POST /api/v1/workforce/leave/balances/allocate** — `allocate_balance`

  Parameters: `request: Request, body: WorkforceLeaveBalanceAllocateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceLeaveBalanceOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/leave/requests** — `list_requests`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), status: str | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), from_date: date | None=Query(default=None), to_date: date | None=Query(default=None), limit: int=Query(default=200, ge=1, le=500), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceLeaveRequestOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope

- **POST /api/v1/workforce/leave/requests** — `create_request`

  Parameters: `request: Request, body: WorkforceLeaveRequestCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceLeaveRequestOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/leave/requests/{request_id}/decision** — `decide_request`

  Parameters: `request: Request, request_id: uuid.UUID, body: WorkforceLeaveRequestDecisionIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceLeaveRequestOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, MANAGER, OWNER; inspect allow/deny branches

#### /api/v1/workforce/payroll — [backend/app/api/v1/workforce/payroll.py](backend/app/api/v1/workforce/payroll.py)

- **GET /api/v1/workforce/payroll/periods** — `list_periods`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), limit: int=Query(default=50, ge=1, le=200), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforcePayrollPeriodOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/payroll/periods** — `create_period`

  Parameters: `request: Request, body: WorkforcePayrollPeriodCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforcePayrollPeriodOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/payroll/periods/{payroll_period_id}/generate** — `generate`

  Parameters: `request: Request, payroll_period_id: uuid.UUID, body: WorkforcePayrollGenerateDraftIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforcePayrollEntryOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches, role-based response redaction

- **GET /api/v1/workforce/payroll/periods/{payroll_period_id}/entries** — `list_entries`

  Parameters: `request: Request, payroll_period_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforcePayrollEntryOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role-based response redaction

- **POST /api/v1/workforce/payroll/periods/{payroll_period_id}/approve** — `approve`

  Parameters: `request: Request, payroll_period_id: uuid.UUID, body: WorkforcePayrollPeriodActionIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforcePayrollPeriodOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/payroll/periods/{payroll_period_id}/mark-paid** — `mark_paid`

  Parameters: `request: Request, payroll_period_id: uuid.UUID, body: WorkforcePayrollPeriodActionIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforcePayrollPeriodOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/payroll/periods/{payroll_period_id}/export** — `export_csv`

  Parameters: `request: Request, payroll_period_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: MANAGER, VIEWER; inspect allow/deny branches, role-based response redaction

- **POST /api/v1/workforce/payroll/adjustments** — `create_adjustment`

  Parameters: `request: Request, body: WorkforcePayrollAdjustmentCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforcePayrollAdjustmentOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **DELETE /api/v1/workforce/payroll/adjustments/{adjustment_id}** — `delete_adjustment`

  Parameters: `request: Request, adjustment_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), payroll_period_id: uuid.UUID=Query(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/payroll/entries/{entry_id}/payslip** — `payslip_preview`

  Parameters: `request: Request, entry_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforcePayslipPreviewOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: EDITOR, OWNER; inspect allow/deny branches, role-based response redaction

- **GET /api/v1/workforce/payroll/entries/{entry_id}/payslip/pdf** — `payslip_pdf`

  Parameters: `request: Request, entry_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `Declared directly in handler`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, employee/team access scope, role literals: MANAGER, VIEWER; inspect allow/deny branches, role-based response redaction

#### /api/v1/workforce/announcements — [backend/app/api/v1/workforce/announcements.py](backend/app/api/v1/workforce/announcements.py)

- **GET /api/v1/workforce/announcements/automation-keys** — `list_automation_keys`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAutomationKeysOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/announcements/attachments/upload** — `upload_announcement_attachment`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), file: UploadFile=File(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAnnouncementAttachmentUploadOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/announcements/templates** — `list_announcement_templates`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceAnnouncementTemplateOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/announcements/templates** — `create_announcement_template`

  Parameters: `request: Request, body: WorkforceAnnouncementTemplateCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAnnouncementTemplateOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **PUT /api/v1/workforce/announcements/templates/{template_id}** — `update_announcement_template`

  Parameters: `template_id: uuid.UUID, request: Request, body: WorkforceAnnouncementTemplateUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAnnouncementTemplateOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/announcements** — `list_announcements`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), include_archived: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceAnnouncementOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/announcements** — `create_announcement`

  Parameters: `request: Request, body: WorkforceAnnouncementCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAnnouncementOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/announcements/{announcement_id}/deliveries** — `list_announcement_deliveries`

  Parameters: `announcement_id: uuid.UUID, request: Request, org_id: uuid.UUID | None=Query(default=None), status: str | None=Query(default=None, description='Filter: PENDING, RETRYING, SENT, FAILED, or ALL'), page: int=Query(default=1, ge=1, le=10000), page_size: int=Query(default=50, ge=1, le=200), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAnnouncementDeliveryListOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **PUT /api/v1/workforce/announcements/{announcement_id}** — `update_announcement`

  Parameters: `request: Request, announcement_id: uuid.UUID, body: WorkforceAnnouncementUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAnnouncementOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/announcements/{announcement_id}/publish** — `publish_announcement`

  Parameters: `request: Request, announcement_id: uuid.UUID, body: WorkforceAnnouncementPublishIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAnnouncementOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/announcements/{announcement_id}/archive** — `archive_announcement`

  Parameters: `request: Request, announcement_id: uuid.UUID, body: WorkforceAnnouncementArchiveIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAnnouncementOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/announcements/{announcement_id}** — `get_announcement`

  Parameters: `announcement_id: uuid.UUID, request: Request, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAnnouncementDetailOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/announcements/{announcement_id}/acknowledge** — `acknowledge_announcement`

  Parameters: `request: Request, announcement_id: uuid.UUID, body: WorkforceAnnouncementAcknowledgeIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceAnnouncementReceiptOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

#### /api/v1/workforce/hr — [backend/app/api/v1/workforce/hr_admin.py](backend/app/api/v1/workforce/hr_admin.py)

- **GET /api/v1/workforce/hr/policies** — `list_policies`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), limit: int=Query(default=200, ge=1, le=500), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforcePolicyOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/hr/policies** — `create_policy`

  Parameters: `request: Request, body: WorkforcePolicyCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforcePolicyOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/hr/policies/{policy_id}/publish** — `publish_policy`

  Parameters: `policy_id: uuid.UUID, request: Request, body: WorkforcePolicyPublishIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforcePolicyOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/hr/policies/{policy_id}/acks** — `list_policy_acks`

  Parameters: `policy_id: uuid.UUID, request: Request, org_id: uuid.UUID | None=Query(default=None), limit: int=Query(default=5000, ge=1, le=10000), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforcePolicyAckOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/hr/policies/{policy_id}/ack** — `acknowledge_policy`

  Parameters: `policy_id: uuid.UUID, request: Request, body: WorkforcePolicyAckCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforcePolicyAckOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/hr/documents/upload** — `upload_document`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), policy_id: uuid.UUID | None=Query(default=None), file: UploadFile=File(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceDocumentOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/hr/documents** — `list_documents`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), policy_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), limit: int=Query(default=500, ge=1, le=2000), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceDocumentOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/hr/documents/{document_id}/deactivate** — `deactivate_document`

  Parameters: `document_id: uuid.UUID, request: Request, body: WorkforceDocumentDeactivateIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `dict`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, sensitive reauthentication, role literals: EDITOR, OWNER; inspect allow/deny branches

- **GET /api/v1/workforce/hr/checklist** — `list_checklist`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), kind: str | None=Query(default=None), include_done: bool=Query(default=True), limit: int=Query(default=5000, ge=1, le=10000), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `list[WorkforceChecklistItemOut]`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **POST /api/v1/workforce/hr/checklist** — `create_checklist_item`

  Parameters: `request: Request, body: WorkforceChecklistItemCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceChecklistItemOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

- **POST /api/v1/workforce/hr/checklist/{item_id}/done** — `set_checklist_done`

  Parameters: `item_id: uuid.UUID, request: Request, body: WorkforceChecklistDoneIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceChecklistItemOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution, role literals: EDITOR, OWNER; inspect allow/deny branches

#### /api/v1/workforce/intelligence — [backend/app/api/v1/workforce/intelligence.py](backend/app/api/v1/workforce/intelligence.py)

- **GET /api/v1/workforce/intelligence/dashboard** — `workforce_dashboard_intel`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), as_of: date | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceDashboardIntelOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

- **GET /api/v1/workforce/intelligence/reports/summary** — `workforce_reports_summary`

  Parameters: `request: Request, org_id: uuid.UUID | None=Query(default=None), from_date: date=Query(..., alias='from'), to_date: date=Query(..., alias='to'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)`

  Response model: `WorkforceReportsSummaryOut`

  Source guards: authenticated user, organization membership/policy, Workforce canonical/header org resolution

### B. Complete backend settings

Code defaults come from Settings; exported variables and the example template can override them. Required means no default. Private environment values are omitted. EMAIL_PROVIDER is validated as smtp/resend; live Resend requires API key and from address.

| Environment variable | Type | Code default | Settings attribute |
| --- | --- | --- | --- |
| `APP_NAME` | `str` | `'AI COO'` | `app_name` |
| `ENV` | `str` | `'development'` | `env` |
| `SECRET_KEY` | `str` | `Required` | `secret_key` |
| `JWT_ALGORITHM` | `str` | `'HS256'` | `jwt_algorithm` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `15` | `access_token_expire_minutes` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `int` | `14` | `refresh_token_expire_days` |
| `DATABASE_URL` | `str` | `Required` | `database_url` |
| `REDIS_URL` | `str` | `Required` | `redis_url` |
| `CORS_ORIGINS` | `str` | `'http://localhost:3000'` | `cors_origins` |
| `RATE_LIMIT_PER_MINUTE` | `int` | `20` | `rate_limit_per_minute` |
| `IDEMPOTENCY_TTL_HOURS` | `int` | `72` | `idempotency_ttl_hours` |
| `AUTH_LOCKOUT_THRESHOLD` | `int` | `6` | `auth_lockout_threshold` |
| `AUTH_LOCKOUT_WINDOW_MINUTES` | `int` | `15` | `auth_lockout_window_minutes` |
| `AUTH_LOCKOUT_DURATION_MINUTES` | `int` | `30` | `auth_lockout_duration_minutes` |
| `PII_ENCRYPTION_KEYS` | `str` | `''` | `pii_encryption_keys` |
| `PII_ENCRYPTION_ACTIVE_KEY_ID` | `str` | `'primary'` | `pii_encryption_active_key_id` |
| `DELETION_GRACE_PERIOD_DAYS` | `int` | `14` | `deletion_grace_period_days` |
| `CSV_MAX_BYTES` | `int` | `5 * 1024 * 1024` | `csv_max_bytes` |
| `ANALYTICS_SUMMARY_CACHE_TTL_SECONDS` | `int` | `5` | `analytics_summary_cache_ttl_seconds` |
| `ALERTS_CACHE_TTL_SECONDS` | `int` | `5` | `alerts_cache_ttl_seconds` |
| `TRANSACTIONS_CACHE_TTL_SECONDS` | `int` | `5` | `transactions_cache_ttl_seconds` |
| `DB_POOL_SIZE` | `int` | `5` | `db_pool_size` |
| `DB_MAX_OVERFLOW` | `int` | `0` | `db_max_overflow` |
| `DB_POOL_TIMEOUT_SECONDS` | `int` | `30` | `db_pool_timeout_seconds` |
| `DB_POOL_RECYCLE_SECONDS` | `int` | `1800` | `db_pool_recycle_seconds` |
| `API_DB_POOL_SIZE` | `int \| None` | `None` | `api_db_pool_size` |
| `API_DB_MAX_OVERFLOW` | `int \| None` | `None` | `api_db_max_overflow` |
| `API_DB_POOL_TIMEOUT_SECONDS` | `int \| None` | `None` | `api_db_pool_timeout_seconds` |
| `API_DB_POOL_RECYCLE_SECONDS` | `int \| None` | `None` | `api_db_pool_recycle_seconds` |
| `WORKER_DB_POOL_SIZE` | `int \| None` | `None` | `worker_db_pool_size` |
| `WORKER_DB_MAX_OVERFLOW` | `int \| None` | `None` | `worker_db_max_overflow` |
| `WORKER_DB_POOL_TIMEOUT_SECONDS` | `int \| None` | `None` | `worker_db_pool_timeout_seconds` |
| `WORKER_DB_POOL_RECYCLE_SECONDS` | `int \| None` | `None` | `worker_db_pool_recycle_seconds` |
| `MINIO_ENDPOINT` | `str` | `'minio:9000'` | `minio_endpoint` |
| `MINIO_PUBLIC_BASE_URL` | `str` | `''` | `minio_public_base_url` |
| `MINIO_ACCESS_KEY` | `str` | `'minioadmin'` | `minio_access_key` |
| `MINIO_SECRET_KEY` | `str` | `'minioadmin'` | `minio_secret_key` |
| `MINIO_BUCKET` | `str` | `'reports'` | `minio_bucket` |
| `MINIO_SECURE` | `bool` | `False` | `minio_secure` |
| `SMTP_HOST` | `str` | `'localhost'` | `smtp_host` |
| `SMTP_PORT` | `int` | `1025` | `smtp_port` |
| `SMTP_USER` | `str` | `''` | `smtp_user` |
| `SMTP_PASSWORD` | `str` | `''` | `smtp_password` |
| `SMTP_STARTTLS` | `bool` | `False` | `smtp_starttls` |
| `SMTP_SSL` | `bool` | `False` | `smtp_ssl` |
| `EMAIL_PROVIDER` | `str` | `'smtp'` | `email_provider` |
| `EMAIL_DRY_RUN` | `bool` | `True` | `email_dry_run` |
| `EMAIL_FROM_NAME` | `str` | `'AI-COO'` | `email_from_name` |
| `EMAIL_FROM_ADDRESS` | `str` | `''` | `email_from_address` |
| `EMAIL_REPLY_TO` | `str` | `''` | `email_reply_to` |
| `RESEND_API_KEY` | `str` | `''` | `resend_api_key` |
| `FRONTEND_URL` | `str` | `'http://localhost:3000'` | `frontend_url` |
| `AUTH_CONFIRMATION_TOKEN_TTL_MINUTES` | `int` | `30` | `auth_confirmation_token_ttl_minutes` |
| `AUTH_CONFIRMATION_CODE_TTL_MINUTES` | `int` | `15` | `auth_confirmation_code_ttl_minutes` |
| `AUTH_CONFIRMATION_MAX_ATTEMPTS` | `int` | `5` | `auth_confirmation_max_attempts` |
| `AI_PROVIDER` | `str` | `'stub'` | `ai_provider` |
| `AI_OPENAI_API_KEY` | `str` | `''` | `ai_openai_api_key` |
| `AI_OPENAI_MODEL` | `str` | `'gpt-4o-mini'` | `ai_openai_model` |
| `AI_OPENAI_BASE_URL` | `str` | `'https://api.openai.com/v1'` | `ai_openai_base_url` |
| `AI_OLLAMA_SERVER_URL` | `str` | `'http://localhost:5000/ai'` | `ai_ollama_server_url` |
| `AI_OLLAMA_SERVER_API_KEY` | `str` | `''` | `ai_ollama_server_api_key` |
| `AI_OLLAMA_SERVER_MODEL` | `str` | `''` | `ai_ollama_server_model` |
| `AI_TIMEOUT_SECONDS` | `int` | `20` | `ai_timeout_seconds` |
| `AUTH_COOKIE_MODE` | `bool` | `False` | `auth_cookie_mode` |
| `ENFORCE_HTTPS` | `bool` | `False` | `enforce_https` |
| `COOKIE_SECURE` | `bool` | `False` | `auth_cookie_secure` |
| `COOKIE_SAMESITE` | `str` | `'lax'` | `auth_cookie_samesite` |
| `ACCESS_COOKIE_NAME` | `str` | `'ai_coo_access_token'` | `access_cookie_name` |
| `REFRESH_COOKIE_NAME` | `str` | `'ai_coo_refresh_token'` | `refresh_cookie_name` |
| `CSRF_COOKIE_NAME` | `str` | `'ai_coo_csrf_token'` | `csrf_cookie_name` |
| `CSRF_HEADER_NAME` | `str` | `'X-CSRF-Token'` | `csrf_header_name` |
| `EXPOSE_INVITE_TOKEN_IN_RESPONSE` | `bool` | `True` | `expose_invite_token_in_response` |
| `MFA_TOTP_ISSUER` | `str` | `'AI COO'` | `mfa_totp_issuer` |
| `RUNTIME_SLO_WINDOW_SECONDS` | `int` | `300` | `runtime_slo_window_seconds` |
| `RUNTIME_SLO_P95_MS` | `float` | `2000.0` | `runtime_slo_p95_ms` |
| `RUNTIME_SLO_ERROR_RATE_PCT` | `float` | `1.0` | `runtime_slo_error_rate_pct` |
| `RUNTIME_SLO_TOP_N` | `int` | `20` | `runtime_slo_top_n` |
| `RUNTIME_QUEUE_LAG_THRESHOLD_SECONDS` | `int` | `180` | `runtime_queue_lag_threshold_seconds` |
| `SENTRY_DSN` | `str` | `''` | `sentry_dsn` |
| `SENTRY_TRACES_SAMPLE_RATE` | `float` | `0.0` | `sentry_traces_sample_rate` |
| `STRIPE_SECRET_KEY` | `str` | `''` | `stripe_secret_key` |
| `STRIPE_PUBLISHABLE_KEY` | `str` | `''` | `stripe_publishable_key` |
| `STRIPE_WEBHOOK_SECRET` | `str` | `''` | `stripe_webhook_secret` |
| `BANK_PROVIDER` | `str` | `'stub'` | `bank_provider` |
| `PLAID_CLIENT_ID` | `str` | `''` | `plaid_client_id` |
| `PLAID_SECRET` | `str` | `''` | `plaid_secret` |
| `PLAID_ENV` | `str` | `'sandbox'` | `plaid_env` |
| `PLAID_PRODUCTS` | `str` | `'transactions'` | `plaid_products` |
| `PLAID_COUNTRY_CODES` | `str` | `'US'` | `plaid_country_codes` |
| `PLAID_WEBHOOK_URL` | `str` | `''` | `plaid_webhook_url` |
| `PLAID_WEBHOOK_SECRET` | `str` | `''` | `plaid_webhook_secret` |

#### Additional environment variables and source locations

Literal process-env, k6, shell substitutions and template declarations are indexed. Dynamic variable names need source review. Workforce canonical scoping is an organization setting, not a global environment variable.

| Variable | Declared/read in |
| --- | --- |
| `ACCESS_COOKIE_NAME` | [.env.example](.env.example) |
| `ACCESS_TOKEN` | [scripts/loadtest/k6-smoke.js](scripts/loadtest/k6-smoke.js) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | [.env.example](.env.example) |
| `AI_OLLAMA_SERVER_API_KEY` | [.env.example](.env.example) |
| `AI_OLLAMA_SERVER_MODEL` | [.env.example](.env.example) |
| `AI_OLLAMA_SERVER_URL` | [.env.example](.env.example) |
| `AI_OPENAI_API_KEY` | [.env.example](.env.example) |
| `AI_OPENAI_BASE_URL` | [.env.example](.env.example) |
| `AI_OPENAI_MODEL` | [.env.example](.env.example) |
| `AI_PROVIDER` | [.env.example](.env.example) |
| `AI_TIMEOUT_SECONDS` | [.env.example](.env.example) |
| `ALERTS_CACHE_TTL_SECONDS` | [.env.example](.env.example) |
| `ANALYTICS_SUMMARY_CACHE_TTL_SECONDS` | [.env.example](.env.example) |
| `API_DB_MAX_OVERFLOW` | [.env.example](.env.example) |
| `API_DB_POOL_RECYCLE_SECONDS` | [.env.example](.env.example) |
| `API_DB_POOL_SIZE` | [.env.example](.env.example) |
| `API_DB_POOL_TIMEOUT_SECONDS` | [.env.example](.env.example) |
| `APP_NAME` | [.env.example](.env.example) |
| `APP_ROLE` | [backend/app/db/session.py](backend/app/db/session.py) |
| `AUTH_CONFIRMATION_CODE_TTL_MINUTES` | [.env.example](.env.example) |
| `AUTH_CONFIRMATION_MAX_ATTEMPTS` | [.env.example](.env.example) |
| `AUTH_CONFIRMATION_TOKEN_TTL_MINUTES` | [.env.example](.env.example) |
| `AUTH_COOKIE_MODE` | [.env.example](.env.example), [backend/app/tests/test_auth_cookie_integration_live.py](backend/app/tests/test_auth_cookie_integration_live.py), [scripts/verify_runtime.py](scripts/verify_runtime.py) |
| `AUTH_LOCKOUT_DURATION_MINUTES` | [.env.example](.env.example) |
| `AUTH_LOCKOUT_THRESHOLD` | [.env.example](.env.example) |
| `AUTH_LOCKOUT_WINDOW_MINUTES` | [.env.example](.env.example) |
| `BANK_PROVIDER` | [.env.example](.env.example) |
| `BASE_URL` | [scripts/loadtest/k6-inventory-churn.js](scripts/loadtest/k6-inventory-churn.js), [scripts/loadtest/k6-many-org-dashboard.js](scripts/loadtest/k6-many-org-dashboard.js), [scripts/loadtest/k6-mixed-churn.js](scripts/loadtest/k6-mixed-churn.js), [scripts/loadtest/k6-read-hotpaths.js](scripts/loadtest/k6-read-hotpaths.js), [scripts/loadtest/k6-report-burst.js](scripts/loadtest/k6-report-burst.js), [scripts/loadtest/k6-runtime-observability.js](scripts/loadtest/k6-runtime-observability.js), [scripts/loadtest/k6-smoke.js](scripts/loadtest/k6-smoke.js), [scripts/loadtest/k6-write-heavy.js](scripts/loadtest/k6-write-heavy.js) |
| `BURST_TARGET_VUS` | [scripts/loadtest/k6-report-burst.js](scripts/loadtest/k6-report-burst.js) |
| `COOKIE_SAMESITE` | [.env.example](.env.example) |
| `COOKIE_SECURE` | [.env.example](.env.example) |
| `CORS_ORIGINS` | [.env.example](.env.example) |
| `CSRF_COOKIE_NAME` | [.env.example](.env.example) |
| `CSRF_HEADER_NAME` | [.env.example](.env.example) |
| `CSV_MAX_BYTES` | [.env.example](.env.example) |
| `DATABASE_URL` | [.env.example](.env.example), [scripts/loadtest/bootstrap_multi_org_perf.py](scripts/loadtest/bootstrap_multi_org_perf.py), [scripts/loadtest/bootstrap_perf.py](scripts/loadtest/bootstrap_perf.py), [scripts/ops/verify_ai_live_mode.py](scripts/ops/verify_ai_live_mode.py) |
| `DB_MAX_OVERFLOW` | [.env.example](.env.example) |
| `DB_POOL_RECYCLE_SECONDS` | [.env.example](.env.example) |
| `DB_POOL_SIZE` | [.env.example](.env.example) |
| `DB_POOL_TIMEOUT_SECONDS` | [.env.example](.env.example) |
| `DELETION_GRACE_PERIOD_DAYS` | [.env.example](.env.example) |
| `DURATION` | [scripts/loadtest/k6-inventory-churn.js](scripts/loadtest/k6-inventory-churn.js), [scripts/loadtest/k6-many-org-dashboard.js](scripts/loadtest/k6-many-org-dashboard.js), [scripts/loadtest/k6-mixed-churn.js](scripts/loadtest/k6-mixed-churn.js), [scripts/loadtest/k6-read-hotpaths.js](scripts/loadtest/k6-read-hotpaths.js), [scripts/loadtest/k6-runtime-observability.js](scripts/loadtest/k6-runtime-observability.js), [scripts/loadtest/k6-write-heavy.js](scripts/loadtest/k6-write-heavy.js) |
| `E2E_API_REQUEST_TIMEOUT_MS` | [frontend/e2e/mfa-session.spec.ts](frontend/e2e/mfa-session.spec.ts), [frontend/e2e/stripe-integration.spec.ts](frontend/e2e/stripe-integration.spec.ts) |
| `E2E_API_RETRY_ATTEMPTS` | [frontend/e2e/mfa-session.spec.ts](frontend/e2e/mfa-session.spec.ts), [frontend/e2e/stripe-integration.spec.ts](frontend/e2e/stripe-integration.spec.ts) |
| `E2E_API_RETRY_DELAY_MS` | [frontend/e2e/mfa-session.spec.ts](frontend/e2e/mfa-session.spec.ts), [frontend/e2e/stripe-integration.spec.ts](frontend/e2e/stripe-integration.spec.ts) |
| `E2E_API_URL` | [frontend/e2e/auth-confirm-ui.spec.ts](frontend/e2e/auth-confirm-ui.spec.ts), [frontend/e2e/cookie-csrf.spec.ts](frontend/e2e/cookie-csrf.spec.ts), [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts), [frontend/e2e/global-setup.ts](frontend/e2e/global-setup.ts), [frontend/e2e/mfa-session.spec.ts](frontend/e2e/mfa-session.spec.ts), [frontend/e2e/ops-flow.spec.ts](frontend/e2e/ops-flow.spec.ts), [frontend/e2e/polish.spec.ts](frontend/e2e/polish.spec.ts), [frontend/e2e/rbac-viewer-api.spec.ts](frontend/e2e/rbac-viewer-api.spec.ts), [frontend/e2e/rbac-viewer-settings-api.spec.ts](frontend/e2e/rbac-viewer-settings-api.spec.ts), [frontend/e2e/stripe-integration.spec.ts](frontend/e2e/stripe-integration.spec.ts), [frontend/e2e/workforce-communications-failure-states.spec.ts](frontend/e2e/workforce-communications-failure-states.spec.ts), [frontend/e2e/workforce-hr-admin.spec.ts](frontend/e2e/workforce-hr-admin.spec.ts), [frontend/e2e/workforce-leave-workflow.spec.ts](frontend/e2e/workforce-leave-workflow.spec.ts), [frontend/e2e/workforce-onboarding-offboarding.spec.ts](frontend/e2e/workforce-onboarding-offboarding.spec.ts), [frontend/e2e/workforce-payroll-workflow.spec.ts](frontend/e2e/workforce-payroll-workflow.spec.ts), [frontend/e2e/workforce-phase1.spec.ts](frontend/e2e/workforce-phase1.spec.ts), [frontend/e2e/workforce-phase7-intelligence.spec.ts](frontend/e2e/workforce-phase7-intelligence.spec.ts), [frontend/e2e/workforce-rbac-negative.spec.ts](frontend/e2e/workforce-rbac-negative.spec.ts), [frontend/e2e/workforce-state-matrix.spec.ts](frontend/e2e/workforce-state-matrix.spec.ts) |
| `E2E_AUTH_MODE` | [frontend/e2e/cookie-csrf.spec.ts](frontend/e2e/cookie-csrf.spec.ts), [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts), [frontend/e2e/global-setup.ts](frontend/e2e/global-setup.ts) |
| `E2E_BASE_URL` | [frontend/playwright.config.ts](frontend/playwright.config.ts) |
| `E2E_CLEAN_NEXT_CACHE` | [frontend/playwright.config.ts](frontend/playwright.config.ts) |
| `E2E_CSRF_COOKIE_NAME` | [frontend/e2e/cookie-csrf.spec.ts](frontend/e2e/cookie-csrf.spec.ts), [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts), [frontend/e2e/workforce-hr-admin.spec.ts](frontend/e2e/workforce-hr-admin.spec.ts) |
| `E2E_CSRF_HEADER_NAME` | [frontend/e2e/cookie-csrf.spec.ts](frontend/e2e/cookie-csrf.spec.ts), [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts), [frontend/e2e/workforce-hr-admin.spec.ts](frontend/e2e/workforce-hr-admin.spec.ts) |
| `E2E_FORCE_VIEWPORT` | [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts), [frontend/e2e/responsive-mobile.spec.ts](frontend/e2e/responsive-mobile.spec.ts) |
| `E2E_INVITE_RETRY_ATTEMPTS` | [frontend/e2e/ops-flow.spec.ts](frontend/e2e/ops-flow.spec.ts), [frontend/e2e/rbac-viewer-api.spec.ts](frontend/e2e/rbac-viewer-api.spec.ts), [frontend/e2e/rbac-viewer-settings-api.spec.ts](frontend/e2e/rbac-viewer-settings-api.spec.ts) |
| `E2E_INVITE_RETRY_DELAY_MS` | [frontend/e2e/ops-flow.spec.ts](frontend/e2e/ops-flow.spec.ts), [frontend/e2e/rbac-viewer-api.spec.ts](frontend/e2e/rbac-viewer-api.spec.ts), [frontend/e2e/rbac-viewer-settings-api.spec.ts](frontend/e2e/rbac-viewer-settings-api.spec.ts) |
| `E2E_LOGIN_BACKOFF_BASE_MS` | [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts) |
| `E2E_LOGIN_BACKOFF_MAX_MS` | [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts) |
| `E2E_LOGIN_RETRY_LIMIT` | [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts) |
| `E2E_ORG_ID` | [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts), [scripts/smoke_mvp.py](scripts/smoke_mvp.py) |
| `E2E_PLAID_PUBLIC_TOKEN` | [frontend/e2e/plaid-integration.spec.ts](frontend/e2e/plaid-integration.spec.ts) |
| `E2E_PLAID_SANDBOX` | [frontend/e2e/plaid-integration.spec.ts](frontend/e2e/plaid-integration.spec.ts) |
| `E2E_RECON_WAIT_MS` | [frontend/e2e/stripe-integration.spec.ts](frontend/e2e/stripe-integration.spec.ts) |
| `E2E_REG_RETRY_ATTEMPTS` | [frontend/e2e/ops-flow.spec.ts](frontend/e2e/ops-flow.spec.ts) |
| `E2E_REG_RETRY_DELAY_MS` | [frontend/e2e/ops-flow.spec.ts](frontend/e2e/ops-flow.spec.ts) |
| `E2E_SKIP_AUTH_PREFLIGHT` | [frontend/e2e/global-setup.ts](frontend/e2e/global-setup.ts) |
| `E2E_SSE` | [frontend/e2e/sse-fallback.spec.ts](frontend/e2e/sse-fallback.spec.ts) |
| `E2E_STRIPE_LIVE` | [frontend/e2e/stripe-integration.spec.ts](frontend/e2e/stripe-integration.spec.ts) |
| `E2E_STRIPE_SECRET_KEY` | [frontend/e2e/stripe-integration.spec.ts](frontend/e2e/stripe-integration.spec.ts) |
| `E2E_STRIPE_WEBHOOK_SECRET` | [frontend/e2e/stripe-integration.spec.ts](frontend/e2e/stripe-integration.spec.ts) |
| `E2E_USER_EMAIL` | [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts), [frontend/e2e/full-flow.spec.ts](frontend/e2e/full-flow.spec.ts), [scripts/smoke_mvp.py](scripts/smoke_mvp.py) |
| `E2E_USER_PASSWORD` | [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts), [scripts/smoke_mvp.py](scripts/smoke_mvp.py) |
| `E2E_USE_EXTERNAL_BASE_URL` | [frontend/playwright.config.ts](frontend/playwright.config.ts) |
| `E2E_USE_SEEDED` | [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts) |
| `E2E_VISUAL` | [frontend/e2e/visual.spec.ts](frontend/e2e/visual.spec.ts) |
| `E2E_WEB_SERVER_MODE` | [frontend/playwright.config.ts](frontend/playwright.config.ts) |
| `E2E_WORKERS` | [frontend/playwright.config.ts](frontend/playwright.config.ts) |
| `EMAIL_DRY_RUN` | [.env.example](.env.example) |
| `EMAIL_FROM_ADDRESS` | [.env.example](.env.example) |
| `EMAIL_FROM_NAME` | [.env.example](.env.example) |
| `EMAIL_PROVIDER` | [.env.example](.env.example) |
| `EMAIL_REPLY_TO` | [.env.example](.env.example) |
| `ENFORCE_HTTPS` | [.env.example](.env.example) |
| `ENV` | [.env.example](.env.example) |
| `ENV_FILE` | [.env.example](.env.example), [docker-compose.yml](docker-compose.yml) |
| `EXPOSE_INVITE_TOKEN_IN_RESPONSE` | [.env.example](.env.example) |
| `FROM_DATE` | [scripts/loadtest/k6-smoke.js](scripts/loadtest/k6-smoke.js) |
| `FRONTEND_URL` | [.env.example](.env.example) |
| `IDEMPOTENCY_TTL_HOURS` | [.env.example](.env.example) |
| `INTEGRATION_BASE_URL` | [backend/app/tests/test_api_integration_live.py](backend/app/tests/test_api_integration_live.py), [backend/app/tests/test_auth_cookie_integration_live.py](backend/app/tests/test_auth_cookie_integration_live.py), [backend/app/tests/test_plaid_sandbox_live.py](backend/app/tests/test_plaid_sandbox_live.py), [backend/app/tests/test_stripe_sandbox_live.py](backend/app/tests/test_stripe_sandbox_live.py) |
| `JWT_ALGORITHM` | [.env.example](.env.example) |
| `MAX_VUS` | [scripts/loadtest/k6-inventory-churn.js](scripts/loadtest/k6-inventory-churn.js), [scripts/loadtest/k6-mixed-churn.js](scripts/loadtest/k6-mixed-churn.js), [scripts/loadtest/k6-read-hotpaths.js](scripts/loadtest/k6-read-hotpaths.js), [scripts/loadtest/k6-runtime-observability.js](scripts/loadtest/k6-runtime-observability.js), [scripts/loadtest/k6-write-heavy.js](scripts/loadtest/k6-write-heavy.js) |
| `MFA_ACTION_PASSWORD_MIN` | [frontend/src/app/app/settings/page.tsx](frontend/src/app/app/settings/page.tsx) |
| `MFA_TOTP_ISSUER` | [.env.example](.env.example) |
| `MINIO_ACCESS_KEY` | [.env.example](.env.example), [docker-compose.yml](docker-compose.yml) |
| `MINIO_BUCKET` | [.env.example](.env.example) |
| `MINIO_ENDPOINT` | [.env.example](.env.example) |
| `MINIO_PUBLIC_BASE_URL` | [.env.example](.env.example) |
| `MINIO_SECRET_KEY` | [.env.example](.env.example), [docker-compose.yml](docker-compose.yml) |
| `MINIO_SECURE` | [.env.example](.env.example) |
| `NEXT_INTERNAL_API_URL` | [.env.example](.env.example), [frontend/src/lib/api/server.ts](frontend/src/lib/api/server.ts) |
| `NEXT_PUBLIC_API_BASE_URL` | [.env.example](.env.example), [frontend/src/features/notifications/hooks.ts](frontend/src/features/notifications/hooks.ts), [frontend/src/lib/api/client.ts](frontend/src/lib/api/client.ts), [frontend/src/lib/api/server.ts](frontend/src/lib/api/server.ts) |
| `NEXT_PUBLIC_API_URL` | [.env.example](.env.example), [frontend/src/features/notifications/hooks.ts](frontend/src/features/notifications/hooks.ts), [frontend/src/lib/api/client.ts](frontend/src/lib/api/client.ts), [frontend/src/lib/api/server.ts](frontend/src/lib/api/server.ts) |
| `NEXT_PUBLIC_AUTH_MODE` | [.env.example](.env.example), [frontend/src/features/auth/hooks.ts](frontend/src/features/auth/hooks.ts), [frontend/src/features/notifications/hooks.ts](frontend/src/features/notifications/hooks.ts), [frontend/src/features/settings/hooks.ts](frontend/src/features/settings/hooks.ts), [frontend/src/lib/api/client.ts](frontend/src/lib/api/client.ts) |
| `NEXT_PUBLIC_BUDGET_ALERT_THRESHOLD_PCT` | [.env.example](.env.example) |
| `NEXT_PUBLIC_CSRF_COOKIE_NAME` | [.env.example](.env.example), [frontend/src/lib/api/client.ts](frontend/src/lib/api/client.ts) |
| `NEXT_PUBLIC_CSRF_HEADER_NAME` | [.env.example](.env.example), [frontend/src/lib/api/client.ts](frontend/src/lib/api/client.ts) |
| `NEXT_PUBLIC_CSV_MAX_BYTES` | [.env.example](.env.example), [frontend/src/features/transactions/services/csv.ts](frontend/src/features/transactions/services/csv.ts) |
| `NEXT_PUBLIC_MINIO_PUBLIC_BASE_URL` | [.env.example](.env.example), [frontend/src/features/reports/hooks.ts](frontend/src/features/reports/hooks.ts) |
| `NEXT_PUBLIC_PLAID_LINK_SCRIPT_URL` | [.env.example](.env.example), [frontend/src/app/app/settings/page.tsx](frontend/src/app/app/settings/page.tsx) |
| `NEXT_PUBLIC_SSE_FAILURE_THRESHOLD` | [.env.example](.env.example), [frontend/src/features/notifications/hooks.ts](frontend/src/features/notifications/hooks.ts) |
| `NEXT_PUBLIC_SSE_FALLBACK_POLL_INTERVAL_MS` | [.env.example](.env.example), [frontend/src/features/notifications/hooks.ts](frontend/src/features/notifications/hooks.ts) |
| `NEXT_PUBLIC_SSE_RECONNECT_DELAY_MS` | [.env.example](.env.example), [frontend/src/features/notifications/hooks.ts](frontend/src/features/notifications/hooks.ts) |
| `ORG_ID` | [scripts/loadtest/k6-smoke.js](scripts/loadtest/k6-smoke.js) |
| `PERF_DATABASE_URL` | [scripts/loadtest/bootstrap_multi_org_perf.py](scripts/loadtest/bootstrap_multi_org_perf.py), [scripts/loadtest/bootstrap_perf.py](scripts/loadtest/bootstrap_perf.py) |
| `PII_ENCRYPTION_ACTIVE_KEY_ID` | [.env.example](.env.example) |
| `PII_ENCRYPTION_KEYS` | [.env.example](.env.example) |
| `PLAID_CLIENT_ID` | [.env.example](.env.example) |
| `PLAID_COUNTRY_CODES` | [.env.example](.env.example) |
| `PLAID_ENV` | [.env.example](.env.example) |
| `PLAID_PRODUCTS` | [.env.example](.env.example) |
| `PLAID_SANDBOX_E2E` | [backend/app/tests/test_plaid_sandbox_live.py](backend/app/tests/test_plaid_sandbox_live.py) |
| `PLAID_SECRET` | [.env.example](.env.example) |
| `PLAID_TEST_INSTITUTION_ID` | [backend/app/tests/test_plaid_sandbox_live.py](backend/app/tests/test_plaid_sandbox_live.py) |
| `PLAID_WEBHOOK_SECRET` | [.env.example](.env.example) |
| `PLAID_WEBHOOK_URL` | [.env.example](.env.example) |
| `POSTGRES_DB` | [.env.example](.env.example), [docker-compose.yml](docker-compose.yml), [scripts/ops/backup_postgres.sh](scripts/ops/backup_postgres.sh), [scripts/ops/restore_postgres.sh](scripts/ops/restore_postgres.sh) |
| `POSTGRES_PASSWORD` | [.env.example](.env.example), [docker-compose.yml](docker-compose.yml) |
| `POSTGRES_USER` | [.env.example](.env.example), [docker-compose.yml](docker-compose.yml), [scripts/ops/backup_postgres.sh](scripts/ops/backup_postgres.sh), [scripts/ops/restore_drill.sh](scripts/ops/restore_drill.sh), [scripts/ops/restore_postgres.sh](scripts/ops/restore_postgres.sh) |
| `PREALLOCATED_VUS` | [scripts/loadtest/k6-inventory-churn.js](scripts/loadtest/k6-inventory-churn.js), [scripts/loadtest/k6-mixed-churn.js](scripts/loadtest/k6-mixed-churn.js), [scripts/loadtest/k6-read-hotpaths.js](scripts/loadtest/k6-read-hotpaths.js), [scripts/loadtest/k6-runtime-observability.js](scripts/loadtest/k6-runtime-observability.js), [scripts/loadtest/k6-write-heavy.js](scripts/loadtest/k6-write-heavy.js) |
| `RATE` | [scripts/loadtest/k6-inventory-churn.js](scripts/loadtest/k6-inventory-churn.js), [scripts/loadtest/k6-mixed-churn.js](scripts/loadtest/k6-mixed-churn.js), [scripts/loadtest/k6-read-hotpaths.js](scripts/loadtest/k6-read-hotpaths.js), [scripts/loadtest/k6-runtime-observability.js](scripts/loadtest/k6-runtime-observability.js), [scripts/loadtest/k6-write-heavy.js](scripts/loadtest/k6-write-heavy.js) |
| `RATE_LIMIT_PER_MINUTE` | [.env.example](.env.example) |
| `REDIS_URL` | [.env.example](.env.example) |
| `REFRESH_COOKIE_NAME` | [.env.example](.env.example) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | [.env.example](.env.example) |
| `RESEND_API_KEY` | [.env.example](.env.example) |
| `RUNTIME_METRICS_ENABLED` | [scripts/loadtest/k6-read-hotpaths.js](scripts/loadtest/k6-read-hotpaths.js) |
| `RUNTIME_METRICS_EVERY_N` | [scripts/loadtest/k6-read-hotpaths.js](scripts/loadtest/k6-read-hotpaths.js) |
| `RUNTIME_QUEUE_LAG_THRESHOLD_SECONDS` | [.env.example](.env.example) |
| `RUNTIME_SLO_ERROR_RATE_PCT` | [.env.example](.env.example) |
| `RUNTIME_SLO_P95_MS` | [.env.example](.env.example) |
| `RUNTIME_SLO_TOP_N` | [.env.example](.env.example) |
| `RUNTIME_SLO_WINDOW_SECONDS` | [.env.example](.env.example) |
| `RUN_INTEGRATION_LIVE` | [backend/app/tests/test_api_integration_live.py](backend/app/tests/test_api_integration_live.py), [backend/app/tests/test_auth_cookie_integration_live.py](backend/app/tests/test_auth_cookie_integration_live.py), [backend/app/tests/test_plaid_sandbox_live.py](backend/app/tests/test_plaid_sandbox_live.py), [backend/app/tests/test_stripe_sandbox_live.py](backend/app/tests/test_stripe_sandbox_live.py) |
| `SECRET_KEY` | [.env.example](.env.example) |
| `SENTRY_DSN` | [.env.example](.env.example) |
| `SENTRY_TRACES_SAMPLE_RATE` | [.env.example](.env.example) |
| `SLEEP_SECONDS` | [scripts/loadtest/k6-inventory-churn.js](scripts/loadtest/k6-inventory-churn.js), [scripts/loadtest/k6-many-org-dashboard.js](scripts/loadtest/k6-many-org-dashboard.js), [scripts/loadtest/k6-mixed-churn.js](scripts/loadtest/k6-mixed-churn.js), [scripts/loadtest/k6-read-hotpaths.js](scripts/loadtest/k6-read-hotpaths.js), [scripts/loadtest/k6-report-burst.js](scripts/loadtest/k6-report-burst.js), [scripts/loadtest/k6-runtime-observability.js](scripts/loadtest/k6-runtime-observability.js), [scripts/loadtest/k6-write-heavy.js](scripts/loadtest/k6-write-heavy.js) |
| `SMOKE_AS_OF` | [.env.example](.env.example), [scripts/smoke_workforce_intelligence.py](scripts/smoke_workforce_intelligence.py) |
| `SMOKE_AUTH_MODE` | [.env.example](.env.example), [scripts/smoke_workforce_intelligence.py](scripts/smoke_workforce_intelligence.py) |
| `SMOKE_BASE_URL` | [.env.example](.env.example), [scripts/smoke_workforce_intelligence.py](scripts/smoke_workforce_intelligence.py) |
| `SMOKE_CSRF_COOKIE_NAME` | [scripts/smoke_workforce_intelligence.py](scripts/smoke_workforce_intelligence.py) |
| `SMOKE_CSRF_HEADER_NAME` | [scripts/smoke_workforce_intelligence.py](scripts/smoke_workforce_intelligence.py) |
| `SMOKE_ORG_ID` | [.env.example](.env.example), [scripts/smoke_mvp.py](scripts/smoke_mvp.py), [scripts/smoke_workforce_intelligence.py](scripts/smoke_workforce_intelligence.py) |
| `SMOKE_USER_EMAIL` | [.env.example](.env.example), [scripts/smoke_mvp.py](scripts/smoke_mvp.py), [scripts/smoke_workforce_intelligence.py](scripts/smoke_workforce_intelligence.py) |
| `SMOKE_USER_PASSWORD` | [.env.example](.env.example), [scripts/smoke_mvp.py](scripts/smoke_mvp.py), [scripts/smoke_workforce_intelligence.py](scripts/smoke_workforce_intelligence.py) |
| `SMTP_HOST` | [.env.example](.env.example) |
| `SMTP_PASSWORD` | [.env.example](.env.example) |
| `SMTP_PORT` | [.env.example](.env.example) |
| `SMTP_SSL` | [.env.example](.env.example) |
| `SMTP_STARTTLS` | [.env.example](.env.example) |
| `SMTP_USER` | [.env.example](.env.example) |
| `STRIPE_PUBLISHABLE_KEY` | [.env.example](.env.example) |
| `STRIPE_SANDBOX_E2E` | [backend/app/tests/test_stripe_sandbox_live.py](backend/app/tests/test_stripe_sandbox_live.py) |
| `STRIPE_SECRET_KEY` | [.env.example](.env.example) |
| `STRIPE_WEBHOOK_SECRET` | [.env.example](.env.example) |
| `TO_DATE` | [scripts/loadtest/k6-smoke.js](scripts/loadtest/k6-smoke.js) |
| `TRANSACTIONS_CACHE_TTL_SECONDS` | [.env.example](.env.example) |
| `VUS` | [scripts/loadtest/k6-many-org-dashboard.js](scripts/loadtest/k6-many-org-dashboard.js) |
| `WEEK_START` | [scripts/loadtest/_shared.js](scripts/loadtest/_shared.js) |
| `WORKER_CONCURRENCY` | [.env.example](.env.example), [docker-compose.yml](docker-compose.yml) |
| `WORKER_DB_MAX_OVERFLOW` | [.env.example](.env.example) |
| `WORKER_DB_POOL_RECYCLE_SECONDS` | [.env.example](.env.example) |
| `WORKER_DB_POOL_SIZE` | [.env.example](.env.example) |
| `WORKER_DB_POOL_TIMEOUT_SECONDS` | [.env.example](.env.example) |
| `WORKER_PREFETCH_MULTIPLIER` | [.env.example](.env.example), [docker-compose.yml](docker-compose.yml) |

### C. Database model reference

Fields are direct declarations. Bases/mixins supply inherited UUID/timestamp fields. Column expressions retain foreign keys, precision, defaults, nullability and index flags; table constraints follow when declared. Workforce model fields are not automatically all encrypted or writable by every member.

#### AccountConfirmationToken — `account_confirmation_tokens`

Source: [backend/app/domain/models/account_confirmation_token.py](backend/app/domain/models/account_confirmation_token.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `token_hash` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `code_hash` | `Mapped[str \| None]` | `mapped_column(String(255), nullable=True)` |
| `expires_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False)` |
| `code_expires_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `code_attempts` | `Mapped[int]` | `mapped_column(default=0, nullable=False)` |
| `code_max_attempts` | `Mapped[int]` | `mapped_column(default=5, nullable=False)` |
| `used_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `invalidated_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |

Table constraints: `(Index('ix_account_confirm_token_hash', 'token_hash', unique=True), Index('ix_account_confirm_code_hash', 'code_hash'), Index('ix_account_confirm_user_pending', 'user_id', 'invalidated_at', 'used_at', 'expires_at'))`

#### AIChatMessage — `ai_chat_messages`

Source: [backend/app/domain/models/ai_chat_message.py](backend/app/domain/models/ai_chat_message.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `session_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('ai_chat_sessions.id', ondelete='CASCADE'), nullable=False)` |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `role` | `Mapped[str]` | `mapped_column(String(16), nullable=False)` |
| `content` | `Mapped[str]` | `mapped_column(Text, nullable=False)` |
| `fallback_used` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=False)` |
| `grounding_violations` | `Mapped[list[str]]` | `mapped_column(JSONB, nullable=False, default=list)` |

Table constraints: `(Index('ix_ai_chat_message_session_created', 'session_id', 'created_at'), Index('ix_ai_chat_message_org_created', 'org_id', 'created_at'))`

#### AIChatSession — `ai_chat_sessions`

Source: [backend/app/domain/models/ai_chat_session.py](backend/app/domain/models/ai_chat_session.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `title` | `Mapped[str]` | `mapped_column(String(200), nullable=False, default='New AI chat')` |
| `last_activity_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_ai_chat_session_org_last_activity', 'org_id', 'last_activity_at'), Index('ix_ai_chat_session_org_creator', 'org_id', 'created_by_user_id'))`

#### Alert — `alerts`

Source: [backend/app/domain/models/alert.py](backend/app/domain/models/alert.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `location_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('locations.id'), nullable=True)` |
| `kind` | `Mapped[str]` | `mapped_column(String(32), nullable=False)` |
| `severity` | `Mapped[str]` | `mapped_column(String(20), nullable=False)` |
| `title` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `description` | `Mapped[str]` | `mapped_column(Text, nullable=False)` |
| `meta` | `Mapped[dict]` | `mapped_column(JSONB, default=dict, nullable=False)` |
| `status` | `Mapped[str]` | `mapped_column(String(16), default='OPEN', nullable=False)` |
| `assigned_to_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `assigned_by_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `assigned_at` | `Mapped[datetime \| None]` | `mapped_column(nullable=True)` |
| `acknowledged_at` | `Mapped[datetime \| None]` | `mapped_column(nullable=True)` |

Table constraints: `(Index('ix_alert_org_status_created', 'org_id', 'status', 'created_at'), Index('ix_alert_org_status_assigned', 'org_id', 'status', 'assigned_to_user_id'), Index('ix_alert_org_location_status_created', 'org_id', 'location_id', 'status', 'created_at'))`

#### AuditLog — `audit_logs`

Source: [backend/app/domain/models/audit_log.py](backend/app/domain/models/audit_log.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `actor_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))` |
| `org_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'))` |
| `action` | `Mapped[str]` | `mapped_column(String(100), nullable=False)` |
| `entity_type` | `Mapped[str]` | `mapped_column(String(100), nullable=False)` |
| `entity_id` | `Mapped[str]` | `mapped_column(String(100), nullable=False)` |
| `metadata_json` | `Mapped[dict]` | `mapped_column(JSONB, default=dict, nullable=False)` |

#### BankAccount — `bank_accounts`

Source: [backend/app/domain/models/bank_account.py](backend/app/domain/models/bank_account.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `connection_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('bank_connections.id', ondelete='CASCADE'), nullable=False)` |
| `external_account_id` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `name` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `mask` | `Mapped[str \| None]` | `mapped_column(String(16), nullable=True)` |
| `account_type` | `Mapped[str \| None]` | `mapped_column(String(64), nullable=True)` |
| `account_subtype` | `Mapped[str \| None]` | `mapped_column(String(64), nullable=True)` |
| `currency_code` | `Mapped[str \| None]` | `mapped_column(String(16), nullable=True)` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('connection_id', 'external_account_id', name='uq_bank_acct_conn_external'), Index('ix_bank_acct_org_conn', 'org_id', 'connection_id'))`

#### BankConnection — `bank_connections`

Source: [backend/app/domain/models/bank_connection.py](backend/app/domain/models/bank_connection.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `connected_by_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `provider` | `Mapped[str]` | `mapped_column(String(24), nullable=False, default='PLAID')` |
| `status` | `Mapped[str]` | `mapped_column(String(24), nullable=False, default='ACTIVE')` |
| `external_item_id` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `institution_id` | `Mapped[str \| None]` | `mapped_column(String(255), nullable=True)` |
| `institution_name` | `Mapped[str \| None]` | `mapped_column(String(255), nullable=True)` |
| `access_token_ref` | `Mapped[str]` | `mapped_column(String(1024), nullable=False)` |
| `last_error` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `revoked_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'provider', 'external_item_id', name='uq_bank_conn_org_provider_item'), Index('ix_bank_conn_org_status', 'org_id', 'status'))`

#### BankSyncCursor — `bank_sync_cursors`

Source: [backend/app/domain/models/bank_sync_cursor.py](backend/app/domain/models/bank_sync_cursor.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `connection_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('bank_connections.id', ondelete='CASCADE'), nullable=False, unique=True)` |
| `cursor` | `Mapped[str \| None]` | `mapped_column(String(1024), nullable=True)` |
| `last_synced_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_bank_cursor_org_conn', 'org_id', 'connection_id', unique=True),)`

#### BankSyncRun — `bank_sync_runs`

Source: [backend/app/domain/models/bank_sync_run.py](backend/app/domain/models/bank_sync_run.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `connection_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('bank_connections.id', ondelete='CASCADE'), nullable=False)` |
| `triggered_by_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `status` | `Mapped[str]` | `mapped_column(String(24), nullable=False, default='RUNNING')` |
| `started_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |
| `finished_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `cursor_before` | `Mapped[str \| None]` | `mapped_column(String(1024), nullable=True)` |
| `cursor_after` | `Mapped[str \| None]` | `mapped_column(String(1024), nullable=True)` |
| `fetched_count` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `inserted_count` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `duplicate_count` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `error_message` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_bank_sync_run_org_status_created', 'org_id', 'status', 'created_at'), Index('ix_bank_sync_run_conn_created', 'connection_id', 'created_at'))`

#### BankSyncedTransaction — `bank_synced_transactions`

Source: [backend/app/domain/models/bank_synced_transaction.py](backend/app/domain/models/bank_synced_transaction.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `connection_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('bank_connections.id', ondelete='CASCADE'), nullable=False)` |
| `transaction_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('transactions.id'), nullable=True)` |
| `external_transaction_id` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `posted_date` | `Mapped[date \| None]` | `mapped_column(Date, nullable=True)` |
| `amount` | `Mapped[Decimal \| None]` | `mapped_column(Numeric(14, 2), nullable=True)` |
| `currency_code` | `Mapped[str \| None]` | `mapped_column(String(16), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('connection_id', 'external_transaction_id', name='uq_bank_synced_conn_external_tx'), Index('ix_bank_synced_org_external', 'org_id', 'external_transaction_id'))`

#### Budget — `budgets`

Source: [backend/app/domain/models/budget.py](backend/app/domain/models/budget.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `category` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `period_month` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `budget_type` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='EXPENSE')` |
| `planned_amount` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False)` |
| `notes` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `version` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=1)` |
| `is_current` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'category', 'period_month', 'budget_type', 'version', name='uq_budget_org_category_period_type_version'), Index('ix_budget_org_period_current', 'org_id', 'period_month', 'is_current'), Index('ix_budget_org_type_period', 'org_id', 'budget_type', 'period_month'), Index('ix_budget_org_category_period', 'org_id', 'category', 'period_month'))`

#### Category — `categories`

Source: [backend/app/domain/models/category.py](backend/app/domain/models/category.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `name` | `Mapped[str]` | `mapped_column(String(100), nullable=False)` |
| `type` | `Mapped[str]` | `mapped_column(String(16), nullable=False)` |
| `is_default` | `Mapped[bool]` | `mapped_column(default=True, nullable=False)` |

Table constraints: `(Index('ix_category_org_type', 'org_id', 'type'),)`

#### DeadLetterEvent — `dead_letter_events`

Source: [backend/app/domain/models/dead_letter_event.py](backend/app/domain/models/dead_letter_event.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), nullable=True)` |
| `source_type` | `Mapped[str]` | `mapped_column(String(24), nullable=False)` |
| `source_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), nullable=True)` |
| `source_task_id` | `Mapped[str \| None]` | `mapped_column(String(100), nullable=True)` |
| `source_name` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `status` | `Mapped[str]` | `mapped_column(String(24), nullable=False, default='OPEN')` |
| `attempts` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=1)` |
| `last_error` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `payload` | `Mapped[dict]` | `mapped_column(JSONB, nullable=False, default=dict)` |
| `metadata_json` | `Mapped[dict]` | `mapped_column(JSONB, nullable=False, default=dict)` |
| `first_failed_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |
| `last_failed_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |
| `replayed_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |

Table constraints: `(Index('ix_dead_letter_org_status_created', 'org_id', 'status', 'created_at'), Index('ix_dead_letter_source', 'source_type', 'source_id'))`

#### DeletionRequest — `deletion_requests`

Source: [backend/app/domain/models/deletion_request.py](backend/app/domain/models/deletion_request.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `scope` | `Mapped[str]` | `mapped_column(String(16), nullable=False)` |
| `status` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='PENDING')` |
| `requested_by_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `target_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `target_org_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)` |
| `reason` | `Mapped[str \| None]` | `mapped_column(String(500), nullable=True)` |
| `delete_after` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False)` |
| `processed_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |

Table constraints: `(Index('ix_deletion_requests_due', 'status', 'delete_after'), Index('ix_deletion_requests_scope', 'scope', 'target_user_id', 'target_org_id'))`

#### Role — `Shared mixin or enum`

Source: [backend/app/domain/models/enums.py](backend/app/domain/models/enums.py). Bases: `StrEnum`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `OWNER` | Enum/class value | `'OWNER'` |
| `EDITOR` | Enum/class value | `'EDITOR'` |
| `VIEWER` | Enum/class value | `'VIEWER'` |

#### TransactionType — `Shared mixin or enum`

Source: [backend/app/domain/models/enums.py](backend/app/domain/models/enums.py). Bases: `StrEnum`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `REVENUE` | Enum/class value | `'REVENUE'` |
| `EXPENSE` | Enum/class value | `'EXPENSE'` |

#### AlertKind — `Shared mixin or enum`

Source: [backend/app/domain/models/enums.py](backend/app/domain/models/enums.py). Bases: `StrEnum`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `ANOMALY` | Enum/class value | `'ANOMALY'` |
| `PROFIT_LEAK` | Enum/class value | `'PROFIT_LEAK'` |
| `RUNWAY` | Enum/class value | `'RUNWAY'` |

#### AlertStatus — `Shared mixin or enum`

Source: [backend/app/domain/models/enums.py](backend/app/domain/models/enums.py). Bases: `StrEnum`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `OPEN` | Enum/class value | `'OPEN'` |
| `DISMISSED` | Enum/class value | `'DISMISSED'` |

#### Scenario — `Shared mixin or enum`

Source: [backend/app/domain/models/enums.py](backend/app/domain/models/enums.py). Bases: `StrEnum`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `BASE` | Enum/class value | `'BASE'` |
| `HIGH` | Enum/class value | `'HIGH'` |
| `LOW` | Enum/class value | `'LOW'` |

#### Forecast — `forecasts`

Source: [backend/app/domain/models/forecast.py](backend/app/domain/models/forecast.py). Bases: `Base, UUIDPrimaryKeyMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `month` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `scenario` | `Mapped[str]` | `mapped_column(String(16), nullable=False)` |
| `revenue_pred` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False)` |
| `expense_pred` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False)` |
| `confidence_low` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False)` |
| `confidence_high` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False)` |
| `generated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), nullable=False)` |
| `overrides` | `Mapped[dict \| None]` | `mapped_column(JSONB, nullable=True)` |

Table constraints: `(UniqueConstraint('org_id', 'month', 'scenario', name='uq_forecast_org_month_scenario'), Index('ix_forecast_org_month', 'org_id', 'month'))`

#### IdempotencyKey — `idempotency_keys`

Source: [backend/app/domain/models/idempotency_key.py](backend/app/domain/models/idempotency_key.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), nullable=False, index=True)` |
| `user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), nullable=False, index=True)` |
| `endpoint` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `idempotency_key` | `Mapped[str]` | `mapped_column(String(128), nullable=False)` |
| `request_hash` | `Mapped[str]` | `mapped_column(String(64), nullable=False)` |
| `status_code` | `Mapped[int]` | `mapped_column(Integer, nullable=False)` |
| `response_json` | `Mapped[dict]` | `mapped_column(JSONB, nullable=False, default=dict)` |
| `expires_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, index=True)` |

Table constraints: `(UniqueConstraint('org_id', 'user_id', 'endpoint', 'idempotency_key', name='uq_idempotency_scope_key'),)`

#### ImportMappingProfile — `import_mapping_profiles`

Source: [backend/app/domain/models/import_mapping_profile.py](backend/app/domain/models/import_mapping_profile.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `name` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `column_map` | `Mapped[dict]` | `mapped_column(JSONB, nullable=False, default=dict)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_import_profile_org_name', 'org_id', 'name'), Index('ix_import_profile_org_user', 'org_id', 'user_id'))`

#### InventoryItem — `inventory_items`

Source: [backend/app/domain/models/inventory_item.py](backend/app/domain/models/inventory_item.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `location_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('locations.id'), nullable=True)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `sku` | `Mapped[str]` | `mapped_column(String(80), nullable=False)` |
| `name` | `Mapped[str]` | `mapped_column(String(200), nullable=False)` |
| `unit_cost` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False, default=Decimal('0'))` |
| `reorder_point` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 3), nullable=False, default=Decimal('0'))` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'sku', 'location_id', name='uq_inventory_item_org_sku_location'), Index('ix_inventory_item_org_active', 'org_id', 'is_active'), Index('ix_inventory_item_org_location', 'org_id', 'location_id'))`

#### InventoryPurchaseOrder — `inventory_purchase_orders`

Source: [backend/app/domain/models/inventory_purchase_order.py](backend/app/domain/models/inventory_purchase_order.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `item_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('inventory_items.id', ondelete='CASCADE'), nullable=False)` |
| `location_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('locations.id'), nullable=True)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `quantity` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 3), nullable=False)` |
| `received_qty` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 3), nullable=False, default=Decimal('0'))` |
| `unit_cost` | `Mapped[Decimal \| None]` | `mapped_column(Numeric(14, 2), nullable=True)` |
| `expected_date` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `status` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='OPEN')` |
| `external_ref` | `Mapped[str \| None]` | `mapped_column(String(120), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_inventory_po_org_status_expected', 'org_id', 'status', 'expected_date'), Index('ix_inventory_po_org_item_status', 'org_id', 'item_id', 'status'))`

#### InventorySalesVelocity — `inventory_sales_velocity`

Source: [backend/app/domain/models/inventory_sales_velocity.py](backend/app/domain/models/inventory_sales_velocity.py). Bases: `Base, UUIDPrimaryKeyMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `item_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('inventory_items.id', ondelete='CASCADE'), nullable=False)` |
| `location_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('locations.id'), nullable=True)` |
| `window_days` | `Mapped[int]` | `mapped_column(Integer, nullable=False)` |
| `units_per_day` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 4), nullable=False, default=Decimal('0'))` |
| `basis_start` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `basis_end` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `calculated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'item_id', 'location_id', 'window_days', name='uq_inventory_sales_velocity_org_item_location_window'), Index('ix_inventory_sales_velocity_org_item', 'org_id', 'item_id'))`

#### InventoryStockEvent — `inventory_stock_events`

Source: [backend/app/domain/models/inventory_stock_event.py](backend/app/domain/models/inventory_stock_event.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `item_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('inventory_items.id', ondelete='CASCADE'), nullable=False)` |
| `location_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('locations.id'), nullable=True)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `event_type` | `Mapped[str]` | `mapped_column(String(16), nullable=False)` |
| `quantity` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 3), nullable=False)` |
| `delta_qty` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 3), nullable=False)` |
| `unit_cost` | `Mapped[Decimal \| None]` | `mapped_column(Numeric(14, 2), nullable=True)` |
| `occurred_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |
| `reference` | `Mapped[str \| None]` | `mapped_column(String(120), nullable=True)` |
| `notes` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |

Table constraints: `(Index('ix_inventory_stock_event_org_item_occurred', 'org_id', 'item_id', 'occurred_at'), Index('ix_inventory_stock_event_org_location_occurred', 'org_id', 'location_id', 'occurred_at'))`

#### InventoryStockLevel — `inventory_stock_levels`

Source: [backend/app/domain/models/inventory_stock_level.py](backend/app/domain/models/inventory_stock_level.py). Bases: `Base, UUIDPrimaryKeyMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `item_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('inventory_items.id', ondelete='CASCADE'), nullable=False)` |
| `location_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('locations.id'), nullable=True)` |
| `on_hand_qty` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 3), nullable=False, default=Decimal('0'))` |
| `reserved_qty` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 3), nullable=False, default=Decimal('0'))` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'item_id', 'location_id', name='uq_inventory_stock_level_org_item_location'), Index('ix_inventory_stock_level_org_item', 'org_id', 'item_id'), Index('ix_inventory_stock_level_org_location', 'org_id', 'location_id'))`

#### JobState — `job_states`

Source: [backend/app/domain/models/job_state.py](backend/app/domain/models/job_state.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), nullable=True)` |
| `task_id` | `Mapped[str]` | `mapped_column(String(100), nullable=False, unique=True)` |
| `task_name` | `Mapped[str]` | `mapped_column(String(100), nullable=False)` |
| `job_name` | `Mapped[str]` | `mapped_column(String(100), nullable=False)` |
| `dedupe_key` | `Mapped[str]` | `mapped_column(String(200), nullable=False, unique=True)` |
| `status` | `Mapped[str]` | `mapped_column(String(30), nullable=False, default='PENDING')` |
| `progress` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `payload` | `Mapped[dict]` | `mapped_column(JSONB, default=dict, nullable=False)` |
| `result` | `Mapped[dict \| None]` | `mapped_column(JSONB, nullable=True)` |
| `request_id` | `Mapped[str \| None]` | `mapped_column(String(100), nullable=True)` |
| `correlation_id` | `Mapped[str \| None]` | `mapped_column(String(100), nullable=True)` |
| `last_error` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `traceback_summary` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `retry_count` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `last_retry_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), nullable=False)` |

#### Location — `locations`

Source: [backend/app/domain/models/location.py](backend/app/domain/models/location.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `name` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `code` | `Mapped[str \| None]` | `mapped_column(String(40), nullable=True)` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'name', name='uq_location_org_name'), Index('ix_location_org_active', 'org_id', 'is_active'))`

#### Membership — `memberships`

Source: [backend/app/domain/models/membership.py](backend/app/domain/models/membership.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `role` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='VIEWER')` |

Table constraints: `(UniqueConstraint('user_id', 'org_id', name='uq_membership_user_org'), Index('ix_membership_org_user', 'org_id', 'user_id'))`

#### UUIDPrimaryKeyMixin — `Shared mixin or enum`

Source: [backend/app/domain/models/mixins.py](backend/app/domain/models/mixins.py). Bases: ``.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)` |

#### TimestampMixin — `Shared mixin or enum`

Source: [backend/app/domain/models/mixins.py](backend/app/domain/models/mixins.py). Bases: ``.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `created_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), nullable=False)` |

#### MonthlyAggregate — `monthly_aggregates`

Source: [backend/app/domain/models/monthly_aggregate.py](backend/app/domain/models/monthly_aggregate.py). Bases: `Base, UUIDPrimaryKeyMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `year_month` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `revenue_total` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False, default=0)` |
| `expense_total` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False, default=0)` |
| `net_total` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False, default=0)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), nullable=False)` |

Table constraints: `(UniqueConstraint('org_id', 'year_month', name='uq_agg_org_month'),)`

#### Notification — `notifications`

Source: [backend/app/domain/models/notification.py](backend/app/domain/models/notification.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)` |
| `user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `category` | `Mapped[str]` | `mapped_column(String(64), nullable=False, default='INFO')` |
| `title` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `message` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `link` | `Mapped[str \| None]` | `mapped_column(String(255), nullable=True)` |
| `is_read` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=False)` |
| `metadata_json` | `Mapped[dict]` | `mapped_column(JSONB, nullable=False, default=dict)` |

#### Organization — `organizations`

Source: [backend/app/domain/models/organization.py](backend/app/domain/models/organization.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `name` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `deleted_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True, index=True)` |

#### OrganizationBilling — `organization_billing`

Source: [backend/app/domain/models/organization_billing.py](backend/app/domain/models/organization_billing.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False, unique=True)` |
| `billing_email` | `Mapped[str \| None]` | `mapped_column(String(1024), nullable=True)` |
| `invoice_enabled` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=False)` |
| `plan_label` | `Mapped[str]` | `mapped_column(String(64), nullable=False, default='FREE')` |
| `billing_notes` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `provider` | `Mapped[str]` | `mapped_column(String(32), nullable=False, default='MANUAL')` |
| `customer_id` | `Mapped[str \| None]` | `mapped_column(String(128), nullable=True)` |
| `subscription_id` | `Mapped[str \| None]` | `mapped_column(String(128), nullable=True)` |
| `subscription_status` | `Mapped[str \| None]` | `mapped_column(String(64), nullable=True)` |
| `current_period_end` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `active_price_id` | `Mapped[str \| None]` | `mapped_column(String(128), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |

#### OrganizationInvite — `organization_invites`

Source: [backend/app/domain/models/organization_invite.py](backend/app/domain/models/organization_invite.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `email` | `Mapped[str]` | `mapped_column(String(1024), nullable=False)` |
| `role` | `Mapped[str]` | `mapped_column(String(16), nullable=False)` |
| `invited_by` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `token_hash` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `expires_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False)` |
| `accepted_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |

Table constraints: `(Index('ix_invites_org_email_status', 'org_id', 'email', 'accepted_at'), Index('ix_invites_token_hash', 'token_hash', unique=True))`

#### OrganizationPlan — `organization_plans`

Source: [backend/app/domain/models/organization_plan.py](backend/app/domain/models/organization_plan.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False, unique=True)` |
| `code` | `Mapped[str]` | `mapped_column(String(32), nullable=False, default='FREE')` |
| `transaction_limit_monthly` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=10000)` |
| `report_limit_monthly` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=20)` |
| `ai_summary_limit_monthly` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=500)` |

#### OrganizationSetting — `organization_settings`

Source: [backend/app/domain/models/organization_setting.py](backend/app/domain/models/organization_setting.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), unique=True, nullable=False)` |
| `starting_cash` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), default=0, nullable=False)` |
| `runway_alert_threshold_days` | `Mapped[int]` | `mapped_column(Integer, default=60, nullable=False)` |
| `vendor_concentration_threshold_pct` | `Mapped[Decimal]` | `mapped_column(Numeric(5, 2), default=Decimal('50.00'), nullable=False)` |
| `budget_variance_alert_threshold_pct` | `Mapped[Decimal]` | `mapped_column(Numeric(6, 2), default=Decimal('10.00'), nullable=False)` |
| `misc_growth_multiplier` | `Mapped[Decimal]` | `mapped_column(Numeric(5, 2), default=Decimal('1.40'), nullable=False)` |
| `anomaly_spike_multiplier` | `Mapped[Decimal]` | `mapped_column(Numeric(5, 2), default=Decimal('1.50'), nullable=False)` |
| `owner_mfa_required` | `Mapped[bool]` | `mapped_column(default=False, nullable=False)` |
| `owner_session_max_minutes` | `Mapped[int]` | `mapped_column(Integer, default=120, nullable=False)` |
| `sensitive_action_reauth_minutes` | `Mapped[int]` | `mapped_column(Integer, default=30, nullable=False)` |
| `workforce_org_context_canonical` | `Mapped[bool]` | `mapped_column(default=True, nullable=False)` |

#### OutboxEvent — `outbox_events`

Source: [backend/app/domain/models/outbox_event.py](backend/app/domain/models/outbox_event.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)` |
| `event_type` | `Mapped[str]` | `mapped_column(String(100), nullable=False)` |
| `payload` | `Mapped[dict]` | `mapped_column(JSONB, nullable=False)` |
| `status` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='PENDING')` |
| `attempts` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `max_attempts` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=5)` |
| `available_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |
| `sent_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `last_error` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `correlation_id` | `Mapped[str \| None]` | `mapped_column(String(100), nullable=True)` |
| `dedupe_key` | `Mapped[str \| None]` | `mapped_column(String(255), nullable=True)` |

Table constraints: `(Index('ix_outbox_status_available', 'status', 'available_at'), Index('ix_outbox_org_status_created', 'org_id', 'status', 'created_at'), Index('ix_outbox_dedupe_key', 'dedupe_key', unique=True))`

#### PaymentLedgerEntry — `payment_ledger_entries`

Source: [backend/app/domain/models/payment_ledger_entry.py](backend/app/domain/models/payment_ledger_entry.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), nullable=False)` |
| `connection_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), nullable=True)` |
| `webhook_event_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), nullable=True)` |
| `provider` | `Mapped[str]` | `mapped_column(String(24), nullable=False)` |
| `external_event_id` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `entry_type` | `Mapped[str]` | `mapped_column(String(64), nullable=False)` |
| `direction` | `Mapped[str]` | `mapped_column(String(16), nullable=False)` |
| `amount` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False)` |
| `currency_code` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='USD')` |
| `occurred_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False)` |
| `description` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `metadata_json` | `Mapped[dict]` | `mapped_column(JSONB, nullable=False, default=dict)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'provider', 'external_event_id', 'entry_type', name='uq_payment_ledger_event_type'), Index('ix_payment_ledger_org_occurred', 'org_id', 'occurred_at'), Index('ix_payment_ledger_org_type_occurred', 'org_id', 'entry_type', 'occurred_at'))`

#### PaymentProcessorConnection — `payment_processor_connections`

Source: [backend/app/domain/models/payment_processor_connection.py](backend/app/domain/models/payment_processor_connection.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `connected_by_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `provider` | `Mapped[str]` | `mapped_column(String(24), nullable=False, default='STRIPE')` |
| `status` | `Mapped[str]` | `mapped_column(String(24), nullable=False, default='ACTIVE')` |
| `provider_account_id` | `Mapped[str \| None]` | `mapped_column(String(255), nullable=True)` |
| `metadata_json` | `Mapped[dict]` | `mapped_column(JSONB, nullable=False, default=dict)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'provider', name='uq_payment_conn_org_provider'), Index('ix_payment_conn_org_provider_status', 'org_id', 'provider', 'status'))`

#### PaymentWebhookEvent — `payment_webhook_events`

Source: [backend/app/domain/models/payment_webhook_event.py](backend/app/domain/models/payment_webhook_event.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), nullable=True)` |
| `connection_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), nullable=True)` |
| `provider` | `Mapped[str]` | `mapped_column(String(24), nullable=False)` |
| `provider_event_id` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `event_type` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `status` | `Mapped[str]` | `mapped_column(String(24), nullable=False, default='RECEIVED')` |
| `payload` | `Mapped[dict]` | `mapped_column(JSONB, nullable=False, default=dict)` |
| `error_message` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `received_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |
| `processed_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('provider', 'provider_event_id', name='uq_payment_webhook_provider_event'), Index('ix_payment_webhook_org_status_created', 'org_id', 'status', 'created_at'))`

#### Report — `reports`

Source: [backend/app/domain/models/report.py](backend/app/domain/models/report.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `location_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('locations.id'), nullable=True)` |
| `week_start` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `week_end` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `file_key` | `Mapped[str]` | `mapped_column(String(500), nullable=False)` |
| `created_by` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))` |

Table constraints: `(Index('ix_report_org_week', 'org_id', 'week_start'), Index('uq_report_org_week_global', 'org_id', 'week_start', unique=True, postgresql_where=text('location_id IS NULL')), Index('uq_report_org_week_location', 'org_id', 'week_start', 'location_id', unique=True, postgresql_where=text('location_id IS NOT NULL')))`

#### ScheduleControl — `schedule_controls`

Source: [backend/app/domain/models/schedule_control.py](backend/app/domain/models/schedule_control.py). Bases: `Base`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `name` | `Mapped[str]` | `mapped_column(String(100), primary_key=True)` |
| `paused` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=False)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |

#### TokenSession — `token_sessions`

Source: [backend/app/domain/models/token_session.py](backend/app/domain/models/token_session.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `refresh_token_hash` | `Mapped[str]` | `mapped_column(String(255), nullable=False, unique=True)` |
| `replaced_by_token_hash` | `Mapped[str \| None]` | `mapped_column(String(255), nullable=True)` |
| `expires_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False)` |
| `last_used_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `is_revoked` | `Mapped[bool]` | `mapped_column(Boolean, default=False, nullable=False)` |
| `user_agent` | `Mapped[str \| None]` | `mapped_column(String(1024), nullable=True)` |
| `ip_address` | `Mapped[str \| None]` | `mapped_column(String(255), nullable=True)` |

Table constraints: `(Index('ix_token_user_active', 'user_id', 'is_revoked'),)`

#### Transaction — `transactions`

Source: [backend/app/domain/models/transaction.py](backend/app/domain/models/transaction.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `date` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `amount` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False)` |
| `type` | `Mapped[str]` | `mapped_column(String(16), nullable=False)` |
| `category` | `Mapped[str]` | `mapped_column(String(100), nullable=False)` |
| `location_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('locations.id'), nullable=True)` |
| `vendor` | `Mapped[str \| None]` | `mapped_column(String(200), nullable=True)` |
| `notes` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `created_by` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |

Table constraints: `(Index('ix_tx_org_date', 'org_id', 'date'), Index('ix_tx_org_type_date', 'org_id', 'type', 'date'), Index('ix_tx_org_category_date', 'org_id', 'category', 'date'), Index('ix_tx_org_location_date', 'org_id', 'location_id', 'date'))`

#### TransactionImport — `transaction_imports`

Source: [backend/app/domain/models/transaction_import.py](backend/app/domain/models/transaction_import.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `created_by` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `file_name` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `status` | `Mapped[str]` | `mapped_column(String(20), nullable=False, default='COMPLETED')` |
| `total_rows` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `inserted_count` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `duplicate_count` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `error_count` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `mapping_profile_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('import_mapping_profiles.id'), nullable=True)` |
| `mapping_json` | `Mapped[dict]` | `mapped_column(JSONB, nullable=False, default=dict)` |
| `error_rows_json` | `Mapped[list[dict] \| None]` | `mapped_column(JSONB, nullable=True)` |

Table constraints: `(Index('ix_tx_import_org_created', 'org_id', 'created_at'), Index('ix_tx_import_org_status', 'org_id', 'status'), Index('ix_tx_import_profile', 'mapping_profile_id'))`

#### UsageMeter — `usage_meters`

Source: [backend/app/domain/models/usage_meter.py](backend/app/domain/models/usage_meter.py). Bases: `Base, UUIDPrimaryKeyMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)` |
| `metric` | `Mapped[str]` | `mapped_column(String(64), nullable=False)` |
| `period_start` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `used_count` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `soft_limit` | `Mapped[int]` | `mapped_column(Integer, nullable=False)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'metric', 'period_start', name='uq_usage_org_metric_period'), Index('ix_usage_org_period', 'org_id', 'period_start'))`

#### User — `users`

Source: [backend/app/domain/models/user.py](backend/app/domain/models/user.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `email` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `password_hash` | `Mapped[str]` | `mapped_column(String(255), nullable=False)` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, default=True, nullable=False)` |
| `mfa_enabled` | `Mapped[bool]` | `mapped_column(Boolean, default=False, nullable=False)` |
| `mfa_secret_encrypted` | `Mapped[str \| None]` | `mapped_column(String(512), nullable=True)` |
| `mfa_enabled_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `mfa_recovery_code_hashes` | `Mapped[list[str]]` | `mapped_column(JSON, default=list, nullable=False)` |
| `deleted_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True, index=True)` |

Table constraints: `(UniqueConstraint('email', name='uq_users_email'),)`

#### WorkforceAnnouncement — `workforce_announcements`

Source: [backend/app/domain/models/workforce_announcement.py](backend/app/domain/models/workforce_announcement.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `template_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_announcement_templates.id', ondelete='SET NULL'), nullable=True)` |
| `title` | `Mapped[str]` | `mapped_column(String(240), nullable=False)` |
| `body` | `Mapped[str]` | `mapped_column(Text, nullable=False)` |
| `priority` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='NORMAL')` |
| `status` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='DRAFT')` |
| `published_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `scheduled_publish_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `expires_at` | `Mapped[date \| None]` | `mapped_column(Date, nullable=True)` |
| `pinned` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=False)` |
| `acknowledgement_required` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=False)` |
| `audience_kind` | `Mapped[str]` | `mapped_column(String(24), nullable=False, default='ORG_ALL')` |
| `audience_ids` | `Mapped[list[Any] \| None]` | `mapped_column(JSONB, nullable=True)` |
| `attachments_json` | `Mapped[list[Any] \| None]` | `mapped_column(JSONB, nullable=True)` |
| `send_email_on_publish` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=False)` |
| `automation_dedupe_key` | `Mapped[str \| None]` | `mapped_column(String(128), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_workforce_announcement_org_status', 'org_id', 'status'), Index('ix_workforce_announcement_org_published', 'org_id', 'published_at'), Index('ix_workforce_announcement_org_audience', 'org_id', 'audience_kind'), Index('uq_workforce_ann_org_automation_dedupe', 'org_id', 'automation_dedupe_key', unique=True))`

#### WorkforceAnnouncementDelivery — `workforce_announcement_deliveries`

Source: [backend/app/domain/models/workforce_announcement_delivery.py](backend/app/domain/models/workforce_announcement_delivery.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `announcement_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_announcements.id', ondelete='CASCADE'), nullable=False)` |
| `channel` | `Mapped[str]` | `mapped_column(String(24), nullable=False, default='email')` |
| `user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)` |
| `recipient_email` | `Mapped[str]` | `mapped_column(String(320), nullable=False)` |
| `status` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='PENDING')` |
| `error` | `Mapped[str \| None]` | `mapped_column(Text, nullable=True)` |
| `outbox_event_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('outbox_events.id', ondelete='SET NULL'), nullable=True)` |
| `sent_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_workforce_ann_delivery_announcement', 'announcement_id'), Index('ix_workforce_ann_delivery_org', 'org_id'))`

#### WorkforceAnnouncementReceipt — `workforce_announcement_receipts`

Source: [backend/app/domain/models/workforce_announcement_receipt.py](backend/app/domain/models/workforce_announcement_receipt.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `announcement_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_announcements.id', ondelete='CASCADE'), nullable=False)` |
| `user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)` |
| `read_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `acknowledged_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('announcement_id', 'user_id', name='uq_workforce_announcement_receipt_user'),)`

#### WorkforceAnnouncementTemplate — `workforce_announcement_templates`

Source: [backend/app/domain/models/workforce_announcement_template.py](backend/app/domain/models/workforce_announcement_template.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `name` | `Mapped[str]` | `mapped_column(String(200), nullable=False)` |
| `code` | `Mapped[str \| None]` | `mapped_column(String(64), nullable=True)` |
| `description` | `Mapped[str \| None]` | `mapped_column(String(500), nullable=True)` |
| `body_template` | `Mapped[str]` | `mapped_column(Text, nullable=False)` |
| `automation_key` | `Mapped[str \| None]` | `mapped_column(String(64), nullable=True)` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_workforce_ann_tpl_org', 'org_id'),)`

#### WorkforceAttendanceCorrection — `workforce_attendance_corrections`

Source: [backend/app/domain/models/workforce_attendance_correction.py](backend/app/domain/models/workforce_attendance_correction.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `employee_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_employees.id', ondelete='CASCADE'), nullable=False)` |
| `attendance_record_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_attendance_records.id', ondelete='CASCADE'), nullable=False)` |
| `requested_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `reviewed_by_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `status` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='PENDING')` |
| `reason` | `Mapped[str]` | `mapped_column(String(500), nullable=False)` |
| `proposed_clock_in_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `proposed_clock_out_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `proposed_status` | `Mapped[str \| None]` | `mapped_column(String(16), nullable=True)` |
| `reviewer_note` | `Mapped[str \| None]` | `mapped_column(String(500), nullable=True)` |
| `reviewed_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_workforce_att_corr_org_status', 'org_id', 'status'), Index('ix_workforce_att_corr_org_employee', 'org_id', 'employee_id'), Index('ix_workforce_att_corr_org_record', 'org_id', 'attendance_record_id'))`

#### WorkforceAttendanceRecord — `workforce_attendance_records`

Source: [backend/app/domain/models/workforce_attendance_record.py](backend/app/domain/models/workforce_attendance_record.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `employee_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_employees.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `work_date` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `status` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='PRESENT')` |
| `source` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='CLOCK')` |
| `shift_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_shifts.id', ondelete='SET NULL'), nullable=True)` |
| `shift_assignment_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_shift_assignments.id', ondelete='SET NULL'), nullable=True)` |
| `clock_in_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `clock_out_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `is_late` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=False)` |
| `minutes_late` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `missing_checkout` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=False)` |
| `worked_minutes` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `overtime_minutes` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `payable_hours` | `Mapped[Decimal]` | `mapped_column(Numeric(10, 2), nullable=False, default=Decimal('0'))` |
| `notes` | `Mapped[str \| None]` | `mapped_column(String(500), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'employee_id', 'work_date', name='uq_workforce_attendance_org_emp_date'), Index('ix_workforce_attendance_org_date', 'org_id', 'work_date'), Index('ix_workforce_attendance_org_employee_date', 'org_id', 'employee_id', 'work_date'), Index('ix_workforce_attendance_org_status_date', 'org_id', 'status', 'work_date'), Index('ix_workforce_attendance_org_flags', 'org_id', 'is_late', 'missing_checkout'))`

#### WorkforceChecklistItem — `workforce_checklist_items`

Source: [backend/app/domain/models/workforce_checklist_item.py](backend/app/domain/models/workforce_checklist_item.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `employee_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_employees.id', ondelete='CASCADE'), nullable=False)` |
| `kind` | `Mapped[str]` | `mapped_column(String(16), nullable=False)` |
| `title` | `Mapped[str]` | `mapped_column(String(240), nullable=False)` |
| `details` | `Mapped[str \| None]` | `mapped_column(String(1000), nullable=True)` |
| `due_date` | `Mapped[date \| None]` | `mapped_column(Date, nullable=True)` |
| `is_done` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=False)` |
| `completed_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `completed_by_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_workforce_checklist_org_employee', 'org_id', 'employee_id'), Index('ix_workforce_checklist_org_kind', 'org_id', 'kind'), Index('ix_workforce_checklist_org_kind_done', 'org_id', 'kind', 'is_done'))`

#### WorkforceDepartment — `workforce_departments`

Source: [backend/app/domain/models/workforce_department.py](backend/app/domain/models/workforce_department.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `name` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `code` | `Mapped[str \| None]` | `mapped_column(String(40), nullable=True)` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'name', name='uq_workforce_department_org_name'), UniqueConstraint('org_id', 'code', name='uq_workforce_department_org_code'), Index('ix_workforce_department_org_active', 'org_id', 'is_active'))`

#### WorkforceDocument — `workforce_documents`

Source: [backend/app/domain/models/workforce_document.py](backend/app/domain/models/workforce_document.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `employee_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_employees.id', ondelete='CASCADE'), nullable=True)` |
| `policy_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_policies.id', ondelete='SET NULL'), nullable=True)` |
| `name` | `Mapped[str]` | `mapped_column(String(200), nullable=False)` |
| `content_type` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `size_bytes` | `Mapped[int]` | `mapped_column(nullable=False, default=0)` |
| `object_key` | `Mapped[str]` | `mapped_column(String(512), nullable=False)` |
| `url` | `Mapped[str]` | `mapped_column(String(2000), nullable=False)` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_workforce_document_org_employee', 'org_id', 'employee_id'), Index('ix_workforce_document_org_policy', 'org_id', 'policy_id'), Index('ix_workforce_document_org_active', 'org_id', 'is_active'))`

#### WorkforceEmployee — `workforce_employees`

Source: [backend/app/domain/models/workforce_employee.py](backend/app/domain/models/workforce_employee.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `employee_code` | `Mapped[str \| None]` | `mapped_column(String(40), nullable=True)` |
| `first_name` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `last_name` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `email` | `Mapped[str \| None]` | `mapped_column(String(320), nullable=True)` |
| `phone` | `Mapped[str \| None]` | `mapped_column(String(40), nullable=True)` |
| `department_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_departments.id', ondelete='SET NULL'), nullable=True)` |
| `title_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_titles.id', ondelete='SET NULL'), nullable=True)` |
| `manager_employee_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_employees.id', ondelete='SET NULL'), nullable=True)` |
| `location_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('locations.id', ondelete='SET NULL'), nullable=True)` |
| `employment_type` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='FULL_TIME')` |
| `employment_status` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='ACTIVE')` |
| `start_date` | `Mapped[date \| None]` | `mapped_column(Date, nullable=True)` |
| `end_date` | `Mapped[date \| None]` | `mapped_column(Date, nullable=True)` |
| `contract_start` | `Mapped[date \| None]` | `mapped_column(Date, nullable=True)` |
| `contract_end` | `Mapped[date \| None]` | `mapped_column(Date, nullable=True)` |
| `probation_end` | `Mapped[date \| None]` | `mapped_column(Date, nullable=True)` |
| `salary_type` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='SALARIED')` |
| `base_salary` | `Mapped[Decimal \| None]` | `mapped_column(Numeric(14, 2), nullable=True)` |
| `hourly_rate` | `Mapped[Decimal \| None]` | `mapped_column(Numeric(14, 2), nullable=True)` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'employee_code', name='uq_workforce_employee_org_code'), Index('ix_workforce_employee_org_active', 'org_id', 'is_active'), Index('ix_workforce_employee_org_department', 'org_id', 'department_id'), Index('ix_workforce_employee_org_title', 'org_id', 'title_id'), Index('ix_workforce_employee_org_manager', 'org_id', 'manager_employee_id'), Index('ix_workforce_employee_org_location', 'org_id', 'location_id'))`

#### WorkforceLeaveBalance — `workforce_leave_balances`

Source: [backend/app/domain/models/workforce_leave_balance.py](backend/app/domain/models/workforce_leave_balance.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `employee_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_employees.id', ondelete='CASCADE'), nullable=False)` |
| `leave_type_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_leave_types.id', ondelete='CASCADE'), nullable=False)` |
| `year` | `Mapped[int]` | `mapped_column(Integer, nullable=False)` |
| `allocated_days` | `Mapped[Decimal]` | `mapped_column(Numeric(10, 2), nullable=False, default=Decimal('0'))` |
| `used_days` | `Mapped[Decimal]` | `mapped_column(Numeric(10, 2), nullable=False, default=Decimal('0'))` |
| `pending_days` | `Mapped[Decimal]` | `mapped_column(Numeric(10, 2), nullable=False, default=Decimal('0'))` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'employee_id', 'leave_type_id', 'year', name='uq_workforce_leave_balance_org_emp_type_year'), Index('ix_workforce_leave_balance_org_employee', 'org_id', 'employee_id'), Index('ix_workforce_leave_balance_org_type', 'org_id', 'leave_type_id'), Index('ix_workforce_leave_balance_org_year', 'org_id', 'year'))`

#### WorkforceLeaveRequest — `workforce_leave_requests`

Source: [backend/app/domain/models/workforce_leave_request.py](backend/app/domain/models/workforce_leave_request.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `employee_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_employees.id', ondelete='CASCADE'), nullable=False)` |
| `leave_type_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_leave_types.id', ondelete='RESTRICT'), nullable=False)` |
| `start_date` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `end_date` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `days` | `Mapped[Decimal]` | `mapped_column(Numeric(10, 2), nullable=False, default=Decimal('1'))` |
| `status` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='PENDING')` |
| `reason` | `Mapped[str \| None]` | `mapped_column(String(500), nullable=True)` |
| `reviewed_by_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `reviewed_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `reviewer_note` | `Mapped[str \| None]` | `mapped_column(String(500), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_workforce_leave_req_org_status', 'org_id', 'status'), Index('ix_workforce_leave_req_org_employee_start', 'org_id', 'employee_id', 'start_date'), Index('ix_workforce_leave_req_org_dates', 'org_id', 'start_date', 'end_date'), Index('ix_workforce_leave_req_org_type', 'org_id', 'leave_type_id'))`

#### WorkforceLeaveType — `workforce_leave_types`

Source: [backend/app/domain/models/workforce_leave_type.py](backend/app/domain/models/workforce_leave_type.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `name` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `code` | `Mapped[str \| None]` | `mapped_column(String(40), nullable=True)` |
| `is_paid` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `requires_approval` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'name', name='uq_workforce_leave_type_org_name'), UniqueConstraint('org_id', 'code', name='uq_workforce_leave_type_org_code'), Index('ix_workforce_leave_type_org_active', 'org_id', 'is_active'))`

#### WorkforcePayrollAdjustment — `workforce_payroll_adjustments`

Source: [backend/app/domain/models/workforce_payroll_adjustment.py](backend/app/domain/models/workforce_payroll_adjustment.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `payroll_period_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_payroll_periods.id', ondelete='CASCADE'), nullable=False)` |
| `payroll_entry_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_payroll_entries.id', ondelete='CASCADE'), nullable=False)` |
| `employee_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_employees.id', ondelete='CASCADE'), nullable=False)` |
| `kind` | `Mapped[str]` | `mapped_column(String(20), nullable=False)` |
| `amount` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False, default=Decimal('0'))` |
| `label` | `Mapped[str \| None]` | `mapped_column(String(200), nullable=True)` |
| `notes` | `Mapped[str \| None]` | `mapped_column(String(500), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(Index('ix_workforce_payroll_adj_org_period', 'org_id', 'payroll_period_id'), Index('ix_workforce_payroll_adj_org_entry', 'org_id', 'payroll_entry_id'), Index('ix_workforce_payroll_adj_org_employee', 'org_id', 'employee_id'), Index('ix_workforce_payroll_adj_org_kind', 'org_id', 'kind'))`

#### WorkforcePayrollEntry — `workforce_payroll_entries`

Source: [backend/app/domain/models/workforce_payroll_entry.py](backend/app/domain/models/workforce_payroll_entry.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `payroll_period_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_payroll_periods.id', ondelete='CASCADE'), nullable=False)` |
| `employee_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_employees.id', ondelete='CASCADE'), nullable=False)` |
| `salary_type` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='SALARIED')` |
| `base_salary` | `Mapped[Decimal \| None]` | `mapped_column(Numeric(14, 2), nullable=True)` |
| `hourly_rate` | `Mapped[Decimal \| None]` | `mapped_column(Numeric(14, 2), nullable=True)` |
| `overtime_multiplier` | `Mapped[Decimal]` | `mapped_column(Numeric(6, 2), nullable=False, default=Decimal('1.5'))` |
| `worked_minutes` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `overtime_minutes` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=0)` |
| `payable_hours` | `Mapped[Decimal]` | `mapped_column(Numeric(10, 2), nullable=False, default=Decimal('0'))` |
| `unpaid_leave_deduction` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False, default=Decimal('0'))` |
| `gross_pay` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False, default=Decimal('0'))` |
| `adjustments_total` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False, default=Decimal('0'))` |
| `net_pay` | `Mapped[Decimal]` | `mapped_column(Numeric(14, 2), nullable=False, default=Decimal('0'))` |
| `status` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='DRAFT')` |
| `is_locked` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=False)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'payroll_period_id', 'employee_id', name='uq_workforce_payroll_entry_org_period_emp'), Index('ix_workforce_payroll_entry_org_period', 'org_id', 'payroll_period_id'), Index('ix_workforce_payroll_entry_org_employee', 'org_id', 'employee_id'), Index('ix_workforce_payroll_entry_org_status', 'org_id', 'status'))`

#### WorkforcePayrollPeriod — `workforce_payroll_periods`

Source: [backend/app/domain/models/workforce_payroll_period.py](backend/app/domain/models/workforce_payroll_period.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `start_date` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `end_date` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `status` | `Mapped[str]` | `mapped_column(String(16), nullable=False, default='DRAFT')` |
| `approved_by_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `approved_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `paid_by_user_id` | `Mapped[uuid.UUID \| None]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)` |
| `paid_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'start_date', 'end_date', name='uq_workforce_payroll_period_org_range'), Index('ix_workforce_payroll_period_org_start', 'org_id', 'start_date'), Index('ix_workforce_payroll_period_org_status', 'org_id', 'status'))`

#### WorkforcePolicy — `workforce_policies`

Source: [backend/app/domain/models/workforce_policy.py](backend/app/domain/models/workforce_policy.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `code` | `Mapped[str]` | `mapped_column(String(64), nullable=False)` |
| `title` | `Mapped[str]` | `mapped_column(String(240), nullable=False)` |
| `body` | `Mapped[str]` | `mapped_column(String, nullable=False)` |
| `version` | `Mapped[int]` | `mapped_column(nullable=False, default=1)` |
| `requires_ack` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `published_at` | `Mapped[datetime \| None]` | `mapped_column(DateTime(timezone=True), nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'code', name='uq_workforce_policy_org_code'), Index('ix_workforce_policy_org_active', 'org_id', 'is_active'), Index('ix_workforce_policy_org_published', 'org_id', 'published_at'))`

#### WorkforcePolicyAcknowledgement — `workforce_policy_acknowledgements`

Source: [backend/app/domain/models/workforce_policy_ack.py](backend/app/domain/models/workforce_policy_ack.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `policy_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_policies.id', ondelete='CASCADE'), nullable=False)` |
| `employee_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_employees.id', ondelete='CASCADE'), nullable=False)` |
| `acknowledged_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc))` |
| `acknowledged_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'policy_id', 'employee_id', name='uq_workforce_policy_ack_org_policy_emp'), Index('ix_workforce_policy_ack_org_policy', 'org_id', 'policy_id'), Index('ix_workforce_policy_ack_org_employee', 'org_id', 'employee_id'))`

#### WorkforceShift — `workforce_shifts`

Source: [backend/app/domain/models/workforce_shift.py](backend/app/domain/models/workforce_shift.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `name` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `start_time` | `Mapped[time]` | `mapped_column(nullable=False)` |
| `end_time` | `Mapped[time]` | `mapped_column(nullable=False)` |
| `grace_minutes` | `Mapped[int]` | `mapped_column(Integer, nullable=False, default=5)` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'name', name='uq_workforce_shift_org_name'), Index('ix_workforce_shift_org_active', 'org_id', 'is_active'))`

#### WorkforceShiftAssignment — `workforce_shift_assignments`

Source: [backend/app/domain/models/workforce_shift_assignment.py](backend/app/domain/models/workforce_shift_assignment.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `employee_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_employees.id', ondelete='CASCADE'), nullable=False)` |
| `shift_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('workforce_shifts.id', ondelete='CASCADE'), nullable=False)` |
| `effective_from` | `Mapped[date]` | `mapped_column(Date, nullable=False)` |
| `effective_to` | `Mapped[date \| None]` | `mapped_column(Date, nullable=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'employee_id', 'shift_id', 'effective_from', name='uq_workforce_shift_assignment_org_emp_shift_from'), Index('ix_workforce_shift_assignment_org_employee', 'org_id', 'employee_id'), Index('ix_workforce_shift_assignment_org_shift', 'org_id', 'shift_id'))`

#### WorkforceTitle — `workforce_titles`

Source: [backend/app/domain/models/workforce_title.py](backend/app/domain/models/workforce_title.py). Bases: `Base, UUIDPrimaryKeyMixin, TimestampMixin`.

| Field | Python declaration | Column/default |
| --- | --- | --- |
| `org_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)` |
| `created_by_user_id` | `Mapped[uuid.UUID]` | `mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)` |
| `name` | `Mapped[str]` | `mapped_column(String(120), nullable=False)` |
| `level` | `Mapped[int \| None]` | `mapped_column(Integer, nullable=True)` |
| `is_active` | `Mapped[bool]` | `mapped_column(Boolean, nullable=False, default=True)` |
| `updated_at` | `Mapped[datetime]` | `mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc), onupdate=lambda: datetime.now(tz=timezone.utc))` |

Table constraints: `(UniqueConstraint('org_id', 'name', name='uq_workforce_title_org_name'), Index('ix_workforce_title_org_active', 'org_id', 'is_active'))`

### D. Request and response schema reference

Fields are direct declarations; listed bases supply inherited fields. Field expressions preserve validation/defaults and custom validators are indexed. API response redaction can replace compensation values; do not infer role access from schema types.

#### AISummaryRequest

Source: [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `from_date` | `date` | `Field(alias='from')` |
| `to_date` | `date` | `Field(alias='to')` |

#### AISummaryResponse

Source: [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `headline` | `str` | `Required` |
| `highlights` | `list[str]` | `Required` |
| `risks` | `list[str]` | `Required` |
| `actions` | `list[str]` | `Required` |
| `confidence` | `str` | `Required` |

#### AISummaryOut

Source: [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `summary_json` | `AISummaryResponse` | `Required` |
| `fallback_used` | `bool` | `Required` |

#### AIChatSessionCreateIn

Source: [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `title` | `str \| None` | `Field(default=None, max_length=200)` |

#### AIChatSessionOut

Source: [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py). Bases: `ORMModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `title` | `str` | `Required` |
| `last_activity_at` | `datetime` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### AIChatMessageOut

Source: [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py). Bases: `ORMModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `session_id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID \| None` | `Required` |
| `role` | `str` | `Required` |
| `content` | `str` | `Required` |
| `fallback_used` | `bool` | `Required` |
| `grounding_violations` | `list[str]` | `Required` |
| `created_at` | `datetime` | `Required` |

#### AIChatSessionDetailOut

Source: [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `session` | `AIChatSessionOut` | `Required` |
| `messages` | `list[AIChatMessageOut]` | `Required` |

#### AIChatRequest

Source: [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `session_id` | `uuid.UUID` | `Required` |
| `message` | `str` | `Field(min_length=1, max_length=4000)` |
| `from_date` | `date` | `Field(alias='from')` |
| `to_date` | `date` | `Field(alias='to')` |

#### AIChatOut

Source: [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `session_id` | `uuid.UUID` | `Required` |
| `message` | `AIChatMessageOut` | `Required` |

#### AIProviderHealthOut

Source: [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `provider` | `str` | `Required` |
| `model` | `str \| None` | `None` |
| `configured` | `bool` | `Required` |
| `healthy` | `bool` | `Required` |
| `live_check_performed` | `bool` | `Required` |
| `reason` | `str \| None` | `None` |

#### AIHealthOut

Source: [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `provider` | `AIProviderHealthOut` | `Required` |
| `fallback_ready` | `bool` | `Required` |

#### AlertOut

Source: [backend/app/domain/schemas/alerts.py](backend/app/domain/schemas/alerts.py). Bases: `ORMModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `location_id` | `uuid.UUID \| None` | `None` |
| `kind` | `str` | `Required` |
| `severity` | `str` | `Required` |
| `title` | `str` | `Required` |
| `description` | `str` | `Required` |
| `meta` | `dict` | `Required` |
| `status` | `str` | `Required` |
| `assigned_to_user_id` | `uuid.UUID \| None` | `None` |
| `assigned_by_user_id` | `uuid.UUID \| None` | `None` |
| `assigned_at` | `datetime \| None` | `None` |
| `acknowledged_at` | `datetime \| None` | `None` |
| `created_at` | `datetime` | `Required` |

#### AlertsOut

Source: [backend/app/domain/schemas/alerts.py](backend/app/domain/schemas/alerts.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[AlertOut]` | `Required` |

#### AlertAssignIn

Source: [backend/app/domain/schemas/alerts.py](backend/app/domain/schemas/alerts.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `assignee_user_id` | `uuid.UUID \| None` | `None` |

#### AlertAcknowledgeIn

Source: [backend/app/domain/schemas/alerts.py](backend/app/domain/schemas/alerts.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |

#### AlertHistoryItem

Source: [backend/app/domain/schemas/alerts.py](backend/app/domain/schemas/alerts.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `action` | `str` | `Required` |
| `actor_user_id` | `uuid.UUID \| None` | `Required` |
| `metadata_json` | `dict` | `Required` |
| `created_at` | `datetime` | `Required` |

#### AlertHistoryOut

Source: [backend/app/domain/schemas/alerts.py](backend/app/domain/schemas/alerts.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[AlertHistoryItem]` | `Required` |

#### SummaryOut

Source: [backend/app/domain/schemas/analytics.py](backend/app/domain/schemas/analytics.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `cash_balance` | `Decimal` | `Required` |
| `revenue_mtd` | `Decimal` | `Required` |
| `expenses_mtd` | `Decimal` | `Required` |
| `net_profit_mtd` | `Decimal` | `Required` |
| `burn_rate_monthly` | `Decimal` | `Required` |
| `alerts_count_open` | `int` | `Required` |

#### CashPoint

Source: [backend/app/domain/schemas/analytics.py](backend/app/domain/schemas/analytics.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `date` | `date` | `Required` |
| `revenue` | `Decimal` | `Required` |
| `expense` | `Decimal` | `Required` |
| `net` | `Decimal` | `Required` |

#### CashflowOut

Source: [backend/app/domain/schemas/analytics.py](backend/app/domain/schemas/analytics.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `points` | `list[CashPoint]` | `Required` |

#### RunwayOut

Source: [backend/app/domain/schemas/analytics.py](backend/app/domain/schemas/analytics.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `runway_days` | `int` | `Required` |
| `monthly_burn` | `Decimal` | `Required` |
| `cash_balance` | `Decimal` | `Required` |
| `alert` | `bool` | `Required` |

#### AnalyticsRecomputeOut

Source: [backend/app/domain/schemas/analytics.py](backend/app/domain/schemas/analytics.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `ok` | `bool` | `Required` |
| `job_id` | `str` | `Required` |
| `status` | `str` | `Required` |
| `result` | `dict \| None` | `None` |

#### LocationBenchmarkTotalsOut

Source: [backend/app/domain/schemas/analytics.py](backend/app/domain/schemas/analytics.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `revenue` | `Decimal` | `Required` |
| `expense` | `Decimal` | `Required` |
| `net` | `Decimal` | `Required` |

#### LocationBenchmarkItemOut

Source: [backend/app/domain/schemas/analytics.py](backend/app/domain/schemas/analytics.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `location_id` | `uuid.UUID \| None` | `None` |
| `location_name` | `str` | `Required` |
| `transaction_count` | `int` | `Required` |
| `revenue` | `Decimal` | `Required` |
| `expense` | `Decimal` | `Required` |
| `net` | `Decimal` | `Required` |
| `margin_pct` | `Decimal \| None` | `None` |
| `revenue_share_pct` | `Decimal \| None` | `None` |
| `expense_share_pct` | `Decimal \| None` | `None` |

#### LocationBenchmarkOut

Source: [backend/app/domain/schemas/analytics.py](backend/app/domain/schemas/analytics.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `from_date` | `date` | `Required` |
| `to_date` | `date` | `Required` |
| `totals` | `LocationBenchmarkTotalsOut` | `Required` |
| `locations` | `list[LocationBenchmarkItemOut]` | `Required` |

#### RegisterIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `email` | `EmailStr` | `Required` |
| `password` | `str` | `Field(min_length=8, max_length=128)` |

#### LoginIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `RegisterIn`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `mfa_code` | `str \| None` | `Field(default=None, min_length=6, max_length=6)` |
| `mfa_recovery_code` | `str \| None` | `Field(default=None, min_length=8, max_length=64)` |

#### TokenRefreshIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `refresh_token` | `str \| None` | `None` |

#### LogoutIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `refresh_token` | `str \| None` | `None` |

#### RegisterOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `user_id` | `uuid.UUID` | `Required` |
| `access_token` | `str \| None` | `None` |
| `refresh_token` | `str \| None` | `None` |
| `token_type` | `str` | `'bearer'` |
| `expires_in` | `int \| None` | `None` |
| `account_confirmed` | `bool` | `False` |

#### InviteAcceptIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `token` | `str` | `Required` |
| `password` | `str` | `Field(min_length=8, max_length=128)` |

#### ConfirmIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `token` | `str \| None` | `None` |
| `code` | `str \| None` | `Field(default=None, min_length=6, max_length=6)` |
| `email` | `EmailStr \| None` | `None` |
| `password` | `str \| None` | `Field(default=None, min_length=8, max_length=128)` |

#### ResendConfirmationIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `email` | `EmailStr` | `Required` |

#### ResendConfirmationOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `ok` | `bool` | `Required` |
| `message` | `str` | `Required` |

#### DevConfirmationTokenOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `email` | `EmailStr` | `Required` |
| `token` | `str \| None` | `None` |
| `found` | `bool` | `Required` |

#### TokenOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `access_token` | `str \| None` | `None` |
| `refresh_token` | `str \| None` | `None` |
| `token_type` | `str` | `'bearer'` |
| `expires_in` | `int` | `Required` |

#### MeOrg

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `role` | `str` | `Required` |
| `name` | `str` | `Required` |

#### MeUser

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `email` | `str` | `Required` |
| `created_at` | `datetime` | `Required` |

#### MeOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `user` | `MeUser` | `Required` |
| `orgs` | `list[MeOrg]` | `Required` |

#### MfaSetupIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `password` | `str` | `Field(min_length=8, max_length=128)` |

#### MfaSetupOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `secret` | `str` | `Required` |
| `otpauth_url` | `str` | `Required` |

#### MfaEnableIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `code` | `str` | `Field(min_length=6, max_length=6)` |

#### MfaDisableIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `password` | `str` | `Field(min_length=8, max_length=128)` |
| `code` | `str` | `Field(min_length=6, max_length=6)` |

#### MfaStatusOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `enabled` | `bool` | `Required` |
| `configured` | `bool` | `Required` |
| `enabled_at` | `datetime \| None` | `Required` |
| `recovery_codes_remaining` | `int` | `0` |

#### MfaRecoveryCodesOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `recovery_codes` | `list[str]` | `Required` |

#### MfaRecoveryCodesRegenerateIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `password` | `str` | `Field(min_length=8, max_length=128)` |
| `code` | `str` | `Field(min_length=6, max_length=6)` |

#### SessionOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `created_at` | `datetime` | `Required` |
| `expires_at` | `datetime` | `Required` |
| `last_used_at` | `datetime \| None` | `Required` |
| `user_agent` | `str \| None` | `Required` |
| `ip_address` | `str \| None` | `Required` |
| `is_revoked` | `bool` | `Required` |
| `is_current` | `bool` | `Required` |

#### SessionListOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[SessionOut]` | `Required` |

#### RevokeOthersIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `refresh_token` | `str \| None` | `None` |

#### ReauthIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `password` | `str` | `Field(min_length=8, max_length=128)` |
| `mfa_code` | `str \| None` | `Field(default=None, min_length=6, max_length=6)` |
| `mfa_recovery_code` | `str \| None` | `Field(default=None, min_length=8, max_length=64)` |

#### ReauthOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `ok` | `bool` | `Required` |
| `token` | `str` | `Required` |
| `token_type` | `str` | `'reauth'` |
| `expires_in` | `int` | `Required` |

#### AccountDeletionRequestIn

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `reason` | `str \| None` | `Field(default=None, max_length=500)` |

#### DeletionRequestOut

Source: [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `ok` | `bool` | `Required` |
| `request_id` | `uuid.UUID` | `Required` |
| `delete_after` | `datetime` | `Required` |

#### BillingCheckoutIn

Source: [backend/app/domain/schemas/billing.py](backend/app/domain/schemas/billing.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `price_id` | `str` | `Required` |
| `success_url` | `str` | `Required` |
| `cancel_url` | `str` | `Required` |

#### BillingCheckoutOut

Source: [backend/app/domain/schemas/billing.py](backend/app/domain/schemas/billing.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `url` | `str` | `Required` |

#### BillingPortalIn

Source: [backend/app/domain/schemas/billing.py](backend/app/domain/schemas/billing.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `return_url` | `str` | `Required` |

#### BillingPortalOut

Source: [backend/app/domain/schemas/billing.py](backend/app/domain/schemas/billing.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `url` | `str` | `Required` |

#### BudgetCreateIn

Source: [backend/app/domain/schemas/budget.py](backend/app/domain/schemas/budget.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `category` | `str` | `Field(min_length=1, max_length=120)` |
| `period_month` | `date` | `Required` |
| `budget_type` | `str` | `Field(default='EXPENSE')` |
| `planned_amount` | `Decimal` | `Required` |
| `notes` | `str \| None` | `None` |

#### BudgetUpdateIn

Source: [backend/app/domain/schemas/budget.py](backend/app/domain/schemas/budget.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `planned_amount` | `Decimal` | `Required` |
| `notes` | `str \| None` | `None` |

#### BudgetOut

Source: [backend/app/domain/schemas/budget.py](backend/app/domain/schemas/budget.py). Bases: `ORMModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `category` | `str` | `Required` |
| `period_month` | `date` | `Required` |
| `budget_type` | `str` | `Required` |
| `planned_amount` | `Decimal` | `Required` |
| `notes` | `str \| None` | `Required` |
| `version` | `int` | `Required` |
| `is_current` | `bool` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### BudgetVarianceLineOut

Source: [backend/app/domain/schemas/budget.py](backend/app/domain/schemas/budget.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `category` | `str` | `Required` |
| `budget_type` | `str` | `Required` |
| `planned_amount` | `Decimal` | `Required` |
| `actual_amount` | `Decimal` | `Required` |
| `variance_amount` | `Decimal` | `Required` |
| `variance_pct` | `Decimal \| None` | `None` |

#### BudgetVarianceTotalsOut

Source: [backend/app/domain/schemas/budget.py](backend/app/domain/schemas/budget.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `planned_amount` | `Decimal` | `Required` |
| `actual_amount` | `Decimal` | `Required` |
| `variance_amount` | `Decimal` | `Required` |

#### BudgetVarianceOut

Source: [backend/app/domain/schemas/budget.py](backend/app/domain/schemas/budget.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `period_month` | `date` | `Required` |
| `budget_type` | `str` | `Required` |
| `totals` | `BudgetVarianceTotalsOut` | `Required` |
| `lines` | `list[BudgetVarianceLineOut]` | `Required` |

#### ORMModel

Source: [backend/app/domain/schemas/common.py](backend/app/domain/schemas/common.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |

#### TransactionOut

Source: [backend/app/domain/schemas/common.py](backend/app/domain/schemas/common.py). Bases: `ORMModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `location_id` | `uuid.UUID \| None` | `None` |
| `date` | `date` | `Required` |
| `amount` | `Decimal` | `Required` |
| `type` | `str` | `Required` |
| `category` | `str` | `Required` |
| `vendor` | `str \| None` | `Required` |
| `notes` | `str \| None` | `Required` |
| `created_by` | `uuid.UUID` | `Required` |
| `created_at` | `datetime` | `Required` |

#### ForecastPoint

Source: [backend/app/domain/schemas/forecast.py](backend/app/domain/schemas/forecast.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `month` | `date` | `Required` |
| `revenue_pred` | `Decimal` | `Required` |
| `expense_pred` | `Decimal` | `Required` |
| `confidence_low` | `Decimal` | `Required` |
| `confidence_high` | `Decimal` | `Required` |

#### ForecastOut

Source: [backend/app/domain/schemas/forecast.py](backend/app/domain/schemas/forecast.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `scenarios` | `dict[str, list[ForecastPoint]]` | `Required` |
| `generated_at` | `datetime` | `Required` |

#### ForecastOverrideIn

Source: [backend/app/domain/schemas/forecast.py](backend/app/domain/schemas/forecast.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `month` | `date` | `Required` |
| `revenue_override` | `Decimal \| None` | `None` |
| `expense_override` | `Decimal \| None` | `None` |
| `scenario` | `str` | `Required` |

#### PlaidLinkTokenIn

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |

#### PlaidLinkTokenOut

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `link_token` | `str` | `Required` |
| `expiration` | `str \| None` | `None` |

#### PlaidExchangeIn

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `public_token` | `str` | `Field(min_length=1)` |
| `institution_name` | `str \| None` | `None` |

#### BankAccountOut

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `external_account_id` | `str` | `Required` |
| `name` | `str` | `Required` |
| `mask` | `str \| None` | `Required` |
| `account_type` | `str \| None` | `Required` |
| `account_subtype` | `str \| None` | `Required` |
| `currency_code` | `str \| None` | `Required` |
| `is_active` | `bool` | `Required` |

#### BankConnectionOut

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `provider` | `str` | `Required` |
| `status` | `str` | `Required` |
| `institution_id` | `str \| None` | `Required` |
| `institution_name` | `str \| None` | `Required` |
| `connected_by_user_id` | `uuid.UUID \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |
| `revoked_at` | `datetime \| None` | `Required` |
| `accounts` | `list[BankAccountOut]` | `Field(default_factory=list)` |

#### PlaidExchangeOut

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `connection` | `BankConnectionOut` | `Required` |

#### BankSyncEnqueueOut

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `job_id` | `str` | `Required` |
| `status` | `str` | `Required` |
| `connection_id` | `uuid.UUID` | `Required` |

#### StripeConnectIn

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `provider_account_id` | `str \| None` | `None` |
| `account_label` | `str \| None` | `None` |

#### PaymentConnectionOut

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `provider` | `str` | `Required` |
| `status` | `str` | `Required` |
| `provider_account_id` | `str \| None` | `Required` |
| `connected_by_user_id` | `uuid.UUID \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |
| `metadata_json` | `dict` | `Field(default_factory=dict)` |

#### StripeConnectOut

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `connection` | `PaymentConnectionOut` | `Required` |

#### PaymentTotalsOut

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `inflow` | `Decimal` | `Required` |
| `outflow` | `Decimal` | `Required` |
| `net` | `Decimal` | `Required` |
| `entry_count` | `int` | `Required` |

#### TransactionTotalsOut

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `revenue` | `Decimal` | `Required` |
| `expense` | `Decimal` | `Required` |
| `net` | `Decimal` | `Required` |
| `entry_count` | `int` | `Required` |

#### ReconciliationDeltaOut

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `net` | `Decimal` | `Required` |
| `absolute` | `Decimal` | `Required` |

#### PaymentReconciliationOut

Source: [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `provider` | `str` | `Required` |
| `date_from` | `date` | `Required` |
| `date_to` | `date` | `Required` |
| `processor` | `PaymentTotalsOut` | `Required` |
| `transactions` | `TransactionTotalsOut` | `Required` |
| `delta` | `ReconciliationDeltaOut` | `Required` |

#### InventoryItemCreateIn

Source: [backend/app/domain/schemas/inventory.py](backend/app/domain/schemas/inventory.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `location_id` | `uuid.UUID \| None` | `None` |
| `sku` | `str` | `Field(min_length=1, max_length=80)` |
| `name` | `str` | `Field(min_length=1, max_length=200)` |
| `unit_cost` | `Decimal` | `Field(default=Decimal('0'))` |
| `reorder_point` | `Decimal` | `Field(default=Decimal('0'))` |
| `is_active` | `bool` | `True` |

#### InventoryItemOut

Source: [backend/app/domain/schemas/inventory.py](backend/app/domain/schemas/inventory.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `location_id` | `uuid.UUID \| None` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `sku` | `str` | `Required` |
| `name` | `str` | `Required` |
| `unit_cost` | `Decimal` | `Required` |
| `reorder_point` | `Decimal` | `Required` |
| `is_active` | `bool` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### InventoryStockEventCreateIn

Source: [backend/app/domain/schemas/inventory.py](backend/app/domain/schemas/inventory.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `item_id` | `uuid.UUID` | `Required` |
| `location_id` | `uuid.UUID \| None` | `None` |
| `event_type` | `str` | `Field(min_length=1, max_length=16)` |
| `quantity` | `Decimal` | `Required` |
| `unit_cost` | `Decimal \| None` | `None` |
| `occurred_at` | `datetime \| None` | `None` |
| `reference` | `str \| None` | `Field(default=None, max_length=120)` |
| `notes` | `str \| None` | `None` |

#### InventoryStockEventOut

Source: [backend/app/domain/schemas/inventory.py](backend/app/domain/schemas/inventory.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `item_id` | `uuid.UUID` | `Required` |
| `location_id` | `uuid.UUID \| None` | `Required` |
| `event_type` | `str` | `Required` |
| `quantity` | `Decimal` | `Required` |
| `delta_qty` | `Decimal` | `Required` |
| `unit_cost` | `Decimal \| None` | `Required` |
| `occurred_at` | `datetime` | `Required` |
| `reference` | `str \| None` | `Required` |
| `notes` | `str \| None` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `created_at` | `datetime` | `Required` |

#### InventoryPurchaseOrderCreateIn

Source: [backend/app/domain/schemas/inventory.py](backend/app/domain/schemas/inventory.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `item_id` | `uuid.UUID` | `Required` |
| `location_id` | `uuid.UUID \| None` | `None` |
| `quantity` | `Decimal` | `Required` |
| `unit_cost` | `Decimal \| None` | `None` |
| `expected_date` | `date` | `Required` |
| `external_ref` | `str \| None` | `Field(default=None, max_length=120)` |

#### InventoryPurchaseOrderOut

Source: [backend/app/domain/schemas/inventory.py](backend/app/domain/schemas/inventory.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `item_id` | `uuid.UUID` | `Required` |
| `location_id` | `uuid.UUID \| None` | `Required` |
| `quantity` | `Decimal` | `Required` |
| `received_qty` | `Decimal` | `Required` |
| `unit_cost` | `Decimal \| None` | `Required` |
| `expected_date` | `date` | `Required` |
| `status` | `str` | `Required` |
| `external_ref` | `str \| None` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### InventoryForecastItemOut

Source: [backend/app/domain/schemas/inventory.py](backend/app/domain/schemas/inventory.py). Bases: `ORMModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `item_id` | `uuid.UUID` | `Required` |
| `sku` | `str` | `Required` |
| `name` | `str` | `Required` |
| `location_id` | `uuid.UUID \| None` | `Required` |
| `on_hand_qty` | `Decimal` | `Required` |
| `inbound_open_qty` | `Decimal` | `Required` |
| `units_per_day` | `Decimal` | `Required` |
| `days_of_cover` | `Decimal \| None` | `Required` |
| `projected_stockout_date` | `date \| None` | `Required` |
| `risk_level` | `str` | `Required` |
| `reorder_point` | `Decimal` | `Required` |
| `cogs_exposure_30d` | `Decimal` | `Required` |

#### InventoryForecastOut

Source: [backend/app/domain/schemas/inventory.py](backend/app/domain/schemas/inventory.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `generated_at` | `datetime` | `Required` |
| `lookback_days` | `int` | `Required` |
| `horizon_days` | `int` | `Required` |
| `items` | `list[InventoryForecastItemOut]` | `Required` |
| `high_risk_items` | `int` | `Required` |

#### JobOut

Source: [backend/app/domain/schemas/job.py](backend/app/domain/schemas/job.py). Bases: `ORMModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID \| None` | `Required` |
| `task_id` | `str` | `Required` |
| `task_name` | `str` | `Required` |
| `dedupe_key` | `str` | `Required` |
| `status` | `str` | `Required` |
| `progress` | `int` | `Required` |
| `payload` | `dict` | `Required` |
| `result` | `dict \| None` | `Required` |
| `request_id` | `str \| None` | `Required` |
| `correlation_id` | `str \| None` | `Required` |
| `last_error` | `str \| None` | `Required` |
| `traceback_summary` | `str \| None` | `Required` |
| `retry_count` | `int` | `Required` |
| `last_retry_at` | `datetime \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### JobCommandResult

Source: [backend/app/domain/schemas/job.py](backend/app/domain/schemas/job.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `ok` | `bool` | `Required` |
| `job_id` | `str` | `Required` |
| `status` | `str` | `Required` |
| `new_task_id` | `str \| None` | `None` |

#### JobPageOut

Source: [backend/app/domain/schemas/job.py](backend/app/domain/schemas/job.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[JobOut]` | `Required` |
| `page` | `int` | `Required` |
| `page_size` | `int` | `Required` |
| `total` | `int` | `Required` |

#### LocationCreateIn

Source: [backend/app/domain/schemas/location.py](backend/app/domain/schemas/location.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `name` | `str` | `Field(min_length=1, max_length=120)` |
| `code` | `str \| None` | `Field(default=None, min_length=1, max_length=40)` |
| `is_active` | `bool` | `True` |

#### LocationUpdateIn

Source: [backend/app/domain/schemas/location.py](backend/app/domain/schemas/location.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `name` | `str \| None` | `Field(default=None, min_length=1, max_length=120)` |
| `code` | `str \| None` | `Field(default=None, min_length=1, max_length=40)` |
| `is_active` | `bool \| None` | `None` |

#### LocationOut

Source: [backend/app/domain/schemas/location.py](backend/app/domain/schemas/location.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `name` | `str` | `Required` |
| `code` | `str \| None` | `Required` |
| `is_active` | `bool` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### NotificationOut

Source: [backend/app/domain/schemas/notification.py](backend/app/domain/schemas/notification.py). Bases: `ORMModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID \| None` | `Required` |
| `user_id` | `uuid.UUID \| None` | `Required` |
| `category` | `str` | `Required` |
| `title` | `str` | `Required` |
| `message` | `str \| None` | `Required` |
| `link` | `str \| None` | `Required` |
| `is_read` | `bool` | `Required` |
| `metadata_json` | `dict` | `Required` |
| `created_at` | `datetime` | `Required` |

#### NotificationPageOut

Source: [backend/app/domain/schemas/notification.py](backend/app/domain/schemas/notification.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[NotificationOut]` | `Required` |
| `page` | `int` | `Required` |
| `page_size` | `int` | `Required` |
| `total` | `int` | `Required` |
| `unread_count` | `int` | `Required` |

#### OutboxEventOut

Source: [backend/app/domain/schemas/operations.py](backend/app/domain/schemas/operations.py). Bases: `ORMModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID \| None` | `Required` |
| `event_type` | `str` | `Required` |
| `payload` | `dict` | `Required` |
| `status` | `str` | `Required` |
| `attempts` | `int` | `Required` |
| `max_attempts` | `int` | `Required` |
| `available_at` | `datetime` | `Required` |
| `sent_at` | `datetime \| None` | `Required` |
| `last_error` | `str \| None` | `Required` |
| `correlation_id` | `str \| None` | `Required` |
| `dedupe_key` | `str \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime \| None` | `None` |

#### OutboxPageOut

Source: [backend/app/domain/schemas/operations.py](backend/app/domain/schemas/operations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[OutboxEventOut]` | `Required` |
| `page` | `int` | `Required` |
| `page_size` | `int` | `Required` |
| `total` | `int` | `Required` |
| `counts_by_status` | `dict[str, int]` | `Required` |

#### BeatScheduleItemOut

Source: [backend/app/domain/schemas/operations.py](backend/app/domain/schemas/operations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `name` | `str` | `Required` |
| `task` | `str` | `Required` |
| `schedule` | `str` | `Required` |
| `paused` | `bool` | `Required` |

#### SystemStatusOut

Source: [backend/app/domain/schemas/operations.py](backend/app/domain/schemas/operations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `scheduler` | `list[BeatScheduleItemOut]` | `Required` |
| `system_jobs` | `list[JobOut]` | `Required` |
| `system_job_total` | `int` | `Required` |
| `org_outbox_counts` | `dict[str, int]` | `Required` |

#### RuntimeMetricsOut

Source: [backend/app/domain/schemas/operations.py](backend/app/domain/schemas/operations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `queue_depth_active` | `int` | `Required` |
| `queue_lag_seconds` | `int` | `Required` |
| `queue_lag_breach` | `bool` | `Required` |
| `outbox_pending` | `int` | `Required` |
| `dead_letter_open` | `int` | `Required` |
| `worker_health` | `str` | `Required` |
| `db_active_connections` | `int` | `Required` |
| `auth_lockout_failures_total` | `int` | `0` |
| `auth_lockouts_total` | `int` | `0` |
| `auth_lockout_escalations_total` | `int` | `0` |

#### EndpointSLOOut

Source: [backend/app/domain/schemas/operations.py](backend/app/domain/schemas/operations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `endpoint` | `str` | `Required` |
| `requests` | `int` | `Required` |
| `p95_ms` | `float` | `Required` |
| `error_rate_pct` | `float` | `Required` |
| `breach` | `bool` | `Required` |

#### RuntimeSLOOut

Source: [backend/app/domain/schemas/operations.py](backend/app/domain/schemas/operations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `window_seconds` | `int` | `Required` |
| `p95_threshold_ms` | `float` | `Required` |
| `error_rate_threshold_pct` | `float` | `Required` |
| `total_requests` | `int` | `Required` |
| `endpoints` | `list[EndpointSLOOut]` | `Required` |

#### DeadLetterEventOut

Source: [backend/app/domain/schemas/operations.py](backend/app/domain/schemas/operations.py). Bases: `ORMModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID \| None` | `Required` |
| `source_type` | `str` | `Required` |
| `source_id` | `uuid.UUID \| None` | `Required` |
| `source_task_id` | `str \| None` | `Required` |
| `source_name` | `str` | `Required` |
| `status` | `str` | `Required` |
| `attempts` | `int` | `Required` |
| `last_error` | `str \| None` | `Required` |
| `payload` | `dict` | `Required` |
| `metadata_json` | `dict` | `Required` |
| `first_failed_at` | `datetime` | `Required` |
| `last_failed_at` | `datetime` | `Required` |
| `replayed_at` | `datetime \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime \| None` | `None` |

#### DeadLetterPageOut

Source: [backend/app/domain/schemas/operations.py](backend/app/domain/schemas/operations.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[DeadLetterEventOut]` | `Required` |
| `page` | `int` | `Required` |
| `page_size` | `int` | `Required` |
| `total` | `int` | `Required` |
| `counts_by_status` | `dict[str, int]` | `Required` |

#### OrganizationCreateIn

Source: [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `name` | `str` | `Required` |

#### OrganizationOut

Source: [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `name` | `str` | `Required` |
| `role` | `str \| None` | `None` |

#### InviteIn

Source: [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `email` | `EmailStr` | `Required` |
| `role` | `str` | `Required` |

Methods/validators: `role_allowed`.

#### MemberOut

Source: [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `user_id` | `uuid.UUID` | `Required` |
| `email` | `str` | `Required` |
| `role` | `str` | `Required` |

#### OrgSettingsOut

Source: [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `starting_cash` | `Decimal` | `Required` |
| `runway_alert_threshold_days` | `int` | `Required` |
| `vendor_concentration_threshold_pct` | `Decimal` | `Required` |
| `budget_variance_alert_threshold_pct` | `Decimal` | `Required` |
| `misc_growth_multiplier` | `Decimal` | `Required` |
| `anomaly_spike_multiplier` | `Decimal` | `Required` |
| `owner_mfa_required` | `bool` | `Required` |
| `owner_session_max_minutes` | `int` | `Required` |
| `sensitive_action_reauth_minutes` | `int` | `Required` |
| `workforce_org_context_canonical` | `bool` | `True` |

#### OrgSettingsUpdateIn

Source: [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `starting_cash` | `Decimal \| None` | `None` |
| `runway_alert_threshold_days` | `int \| None` | `None` |
| `vendor_concentration_threshold_pct` | `Decimal \| None` | `None` |
| `budget_variance_alert_threshold_pct` | `Decimal \| None` | `None` |
| `misc_growth_multiplier` | `Decimal \| None` | `None` |
| `anomaly_spike_multiplier` | `Decimal \| None` | `None` |
| `owner_mfa_required` | `bool \| None` | `None` |
| `owner_session_max_minutes` | `int \| None` | `None` |
| `sensitive_action_reauth_minutes` | `int \| None` | `None` |
| `workforce_org_context_canonical` | `bool \| None` | `None` |

Methods/validators: `validate_starting_cash`, `validate_runway_threshold`, `validate_vendor_threshold`, `validate_budget_variance_threshold`, `validate_multipliers`, `validate_security_window_minutes`.

#### PlanUsageMetricOut

Source: [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `used` | `int` | `Required` |
| `limit` | `int` | `Required` |

#### PlanUsageOut

Source: [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `plan_code` | `str` | `Required` |
| `period_start` | `str` | `Required` |
| `metrics` | `dict[str, PlanUsageMetricOut]` | `Required` |

#### OrgBillingOut

Source: [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `billing_email` | `str \| None` | `Required` |
| `invoice_enabled` | `bool` | `Required` |
| `plan_label` | `str` | `Required` |
| `billing_notes` | `str \| None` | `Required` |
| `provider` | `str` | `Required` |
| `customer_id` | `str \| None` | `Required` |
| `subscription_id` | `str \| None` | `Required` |
| `subscription_status` | `str \| None` | `Required` |
| `current_period_end` | `str \| None` | `Required` |
| `active_price_id` | `str \| None` | `Required` |
| `publishable_key` | `str \| None` | `None` |

#### OrgBillingUpdateIn

Source: [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `billing_email` | `EmailStr \| None` | `None` |
| `invoice_enabled` | `bool \| None` | `None` |
| `plan_label` | `str \| None` | `None` |
| `billing_notes` | `str \| None` | `None` |

#### OrgDeletionRequestIn

Source: [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `reason` | `str \| None` | `None` |

#### DeletionRequestItemOut

Source: [backend/app/domain/schemas/privacy.py](backend/app/domain/schemas/privacy.py). Bases: `ORMModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `scope` | `str` | `Required` |
| `status` | `str` | `Required` |
| `requested_by_user_id` | `uuid.UUID \| None` | `Required` |
| `target_user_id` | `uuid.UUID \| None` | `Required` |
| `target_org_id` | `uuid.UUID \| None` | `Required` |
| `reason` | `str \| None` | `Required` |
| `delete_after` | `datetime` | `Required` |
| `processed_at` | `datetime \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### DeletionRequestListOut

Source: [backend/app/domain/schemas/privacy.py](backend/app/domain/schemas/privacy.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[DeletionRequestItemOut]` | `Required` |

#### ReportItem

Source: [backend/app/domain/schemas/reports.py](backend/app/domain/schemas/reports.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `location_id` | `uuid.UUID \| None` | `None` |
| `week_start` | `date` | `Required` |
| `week_end` | `date` | `Required` |
| `created_at` | `datetime` | `Required` |

#### ReportsOut

Source: [backend/app/domain/schemas/reports.py](backend/app/domain/schemas/reports.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[ReportItem]` | `Required` |

#### ReportGenerateOut

Source: [backend/app/domain/schemas/reports.py](backend/app/domain/schemas/reports.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `report_id` | `uuid.UUID \| None` | `None` |
| `job_id` | `str` | `Required` |
| `status` | `str` | `Required` |

#### TransactionCreateIn

Source: [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `location_id` | `uuid.UUID \| None` | `None` |
| `date` | `date_type` | `Required` |
| `amount` | `Decimal` | `Required` |
| `type` | `str` | `Required` |
| `category` | `str` | `Required` |
| `vendor` | `str \| None` | `None` |
| `notes` | `str \| None` | `None` |

#### TransactionUpdateIn

Source: [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `location_id` | `uuid.UUID \| None` | `None` |
| `date` | `date_type \| None` | `None` |
| `amount` | `Decimal \| None` | `None` |
| `category` | `str \| None` | `None` |
| `vendor` | `str \| None` | `None` |
| `notes` | `str \| None` | `None` |

#### TransactionPageOut

Source: [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[TransactionOut]` | `Required` |
| `page` | `int` | `Required` |
| `page_size` | `int` | `Required` |
| `total` | `int` | `Required` |

#### CSVImportOut

Source: [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `import_id` | `str` | `Required` |
| `preview` | `dict` | `Required` |
| `inserted_count` | `int` | `Required` |
| `mapping_profile_id` | `uuid.UUID \| None` | `None` |

#### ImportHistoryItem

Source: [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `file_name` | `str` | `Required` |
| `status` | `str` | `Required` |
| `total_rows` | `int` | `Required` |
| `inserted_count` | `int` | `Required` |
| `duplicate_count` | `int` | `Required` |
| `error_count` | `int` | `Required` |
| `mapping_profile_id` | `uuid.UUID \| None` | `None` |
| `created_at` | `datetime` | `Required` |
| `created_by` | `uuid.UUID` | `Required` |

#### ImportHistoryPageOut

Source: [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[ImportHistoryItem]` | `Required` |
| `page` | `int` | `Required` |
| `page_size` | `int` | `Required` |
| `total` | `int` | `Required` |

#### CSVImportForm

Source: [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `mapping` | `dict[str, str]` | `Field(default_factory=dict)` |
| `profile_id` | `uuid.UUID \| None` | `None` |

#### ImportMappingProfileIn

Source: [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `name` | `str` | `Field(min_length=1, max_length=120)` |
| `column_map` | `dict[str, str]` | `Required` |
| `shared` | `bool` | `False` |

#### ImportMappingProfileUpdateIn

Source: [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `name` | `str \| None` | `Field(default=None, min_length=1, max_length=120)` |
| `column_map` | `dict[str, str] \| None` | `None` |
| `shared` | `bool \| None` | `None` |

#### ImportMappingProfileOut

Source: [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `user_id` | `uuid.UUID \| None` | `Required` |
| `name` | `str` | `Required` |
| `column_map` | `dict[str, str]` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### BulkCategoryRemapIn

Source: [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `from_category` | `str` | `Required` |
| `to_category` | `str` | `Required` |
| `from_date` | `date_type \| None` | `None` |
| `to_date` | `date_type \| None` | `None` |

#### WorkforceDepartmentCreateIn

Source: [backend/app/domain/schemas/workforce.py](backend/app/domain/schemas/workforce.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `name` | `str` | `Field(min_length=1, max_length=120)` |
| `code` | `str \| None` | `Field(default=None, min_length=1, max_length=40)` |
| `is_active` | `bool` | `True` |

#### WorkforceDepartmentUpdateIn

Source: [backend/app/domain/schemas/workforce.py](backend/app/domain/schemas/workforce.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `name` | `str \| None` | `Field(default=None, min_length=1, max_length=120)` |
| `code` | `str \| None` | `Field(default=None, min_length=1, max_length=40)` |
| `is_active` | `bool \| None` | `None` |

#### WorkforceDepartmentOut

Source: [backend/app/domain/schemas/workforce.py](backend/app/domain/schemas/workforce.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `name` | `str` | `Required` |
| `code` | `str \| None` | `Required` |
| `is_active` | `bool` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforceTitleCreateIn

Source: [backend/app/domain/schemas/workforce.py](backend/app/domain/schemas/workforce.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `name` | `str` | `Field(min_length=1, max_length=120)` |
| `level` | `int \| None` | `Field(default=None, ge=0, le=100)` |
| `is_active` | `bool` | `True` |

#### WorkforceTitleUpdateIn

Source: [backend/app/domain/schemas/workforce.py](backend/app/domain/schemas/workforce.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `name` | `str \| None` | `Field(default=None, min_length=1, max_length=120)` |
| `level` | `int \| None` | `Field(default=None, ge=0, le=100)` |
| `is_active` | `bool \| None` | `None` |

#### WorkforceTitleOut

Source: [backend/app/domain/schemas/workforce.py](backend/app/domain/schemas/workforce.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `name` | `str` | `Required` |
| `level` | `int \| None` | `Required` |
| `is_active` | `bool` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforceEmployeeCreateIn

Source: [backend/app/domain/schemas/workforce.py](backend/app/domain/schemas/workforce.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `employee_code` | `str \| None` | `Field(default=None, min_length=1, max_length=40)` |
| `first_name` | `str` | `Field(min_length=1, max_length=120)` |
| `last_name` | `str` | `Field(min_length=1, max_length=120)` |
| `email` | `str \| None` | `Field(default=None, max_length=320)` |
| `phone` | `str \| None` | `Field(default=None, max_length=40)` |
| `department_id` | `uuid.UUID \| None` | `None` |
| `title_id` | `uuid.UUID \| None` | `None` |
| `manager_employee_id` | `uuid.UUID \| None` | `None` |
| `location_id` | `uuid.UUID \| None` | `None` |
| `employment_type` | `str` | `Field(default='FULL_TIME', max_length=16)` |
| `employment_status` | `str` | `Field(default='ACTIVE', max_length=16)` |
| `start_date` | `date \| None` | `None` |
| `end_date` | `date \| None` | `None` |
| `contract_start` | `date \| None` | `None` |
| `contract_end` | `date \| None` | `None` |
| `probation_end` | `date \| None` | `None` |
| `salary_type` | `str` | `Field(default='SALARIED', max_length=16)` |
| `base_salary` | `Decimal \| None` | `None` |
| `hourly_rate` | `Decimal \| None` | `None` |
| `is_active` | `bool` | `True` |

#### WorkforceEmployeeUpdateIn

Source: [backend/app/domain/schemas/workforce.py](backend/app/domain/schemas/workforce.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `employee_code` | `str \| None` | `Field(default=None, min_length=1, max_length=40)` |
| `first_name` | `str \| None` | `Field(default=None, min_length=1, max_length=120)` |
| `last_name` | `str \| None` | `Field(default=None, min_length=1, max_length=120)` |
| `email` | `str \| None` | `Field(default=None, max_length=320)` |
| `phone` | `str \| None` | `Field(default=None, max_length=40)` |
| `department_id` | `uuid.UUID \| None` | `None` |
| `title_id` | `uuid.UUID \| None` | `None` |
| `manager_employee_id` | `uuid.UUID \| None` | `None` |
| `location_id` | `uuid.UUID \| None` | `None` |
| `employment_type` | `str \| None` | `Field(default=None, max_length=16)` |
| `employment_status` | `str \| None` | `Field(default=None, max_length=16)` |
| `start_date` | `date \| None` | `None` |
| `end_date` | `date \| None` | `None` |
| `contract_start` | `date \| None` | `None` |
| `contract_end` | `date \| None` | `None` |
| `probation_end` | `date \| None` | `None` |
| `salary_type` | `str \| None` | `Field(default=None, max_length=16)` |
| `base_salary` | `Decimal \| None` | `None` |
| `hourly_rate` | `Decimal \| None` | `None` |
| `is_active` | `bool \| None` | `None` |

#### WorkforceEmployeeOut

Source: [backend/app/domain/schemas/workforce.py](backend/app/domain/schemas/workforce.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `employee_code` | `str \| None` | `Required` |
| `first_name` | `str` | `Required` |
| `last_name` | `str` | `Required` |
| `email` | `str \| None` | `Required` |
| `phone` | `str \| None` | `Required` |
| `department_id` | `uuid.UUID \| None` | `Required` |
| `title_id` | `uuid.UUID \| None` | `Required` |
| `manager_employee_id` | `uuid.UUID \| None` | `Required` |
| `location_id` | `uuid.UUID \| None` | `Required` |
| `employment_type` | `str` | `Required` |
| `employment_status` | `str` | `Required` |
| `start_date` | `date \| None` | `Required` |
| `end_date` | `date \| None` | `Required` |
| `contract_start` | `date \| None` | `None` |
| `contract_end` | `date \| None` | `None` |
| `probation_end` | `date \| None` | `None` |
| `salary_type` | `str` | `Required` |
| `base_salary` | `Decimal \| None` | `Required` |
| `hourly_rate` | `Decimal \| None` | `Required` |
| `is_active` | `bool` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### AnnouncementAttachmentIn

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `name` | `str` | `Field(min_length=1, max_length=200)` |
| `url` | `str` | `Field(min_length=1, max_length=2000)` |

#### WorkforceAnnouncementCreateIn

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `title` | `str` | `Field(min_length=1, max_length=240)` |
| `body` | `str` | `Field(min_length=1)` |
| `priority` | `str` | `Field(default='NORMAL', max_length=16)` |
| `pinned` | `bool` | `False` |
| `acknowledgement_required` | `bool` | `False` |
| `expires_at` | `date \| None` | `None` |
| `scheduled_publish_at` | `datetime \| None` | `None` |
| `audience_kind` | `str` | `Field(default='ORG_ALL', max_length=24)` |
| `audience_ids` | `list[uuid.UUID] \| None` | `None` |
| `attachments` | `list[AnnouncementAttachmentIn] \| None` | `None` |
| `send_email_on_publish` | `bool` | `False` |
| `template_id` | `uuid.UUID \| None` | `None` |

#### WorkforceAnnouncementUpdateIn

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `title` | `str \| None` | `Field(default=None, min_length=1, max_length=240)` |
| `body` | `str \| None` | `Field(default=None, min_length=1)` |
| `priority` | `str \| None` | `Field(default=None, max_length=16)` |
| `pinned` | `bool \| None` | `None` |
| `acknowledgement_required` | `bool \| None` | `None` |
| `expires_at` | `date \| None` | `None` |
| `scheduled_publish_at` | `datetime \| None` | `None` |
| `audience_kind` | `str \| None` | `Field(default=None, max_length=24)` |
| `audience_ids` | `list[uuid.UUID] \| None` | `None` |
| `audience_ids_clear` | `bool` | `False` |
| `attachments` | `list[AnnouncementAttachmentIn] \| None` | `None` |
| `attachments_clear` | `bool` | `False` |
| `send_email_on_publish` | `bool \| None` | `None` |
| `template_id` | `uuid.UUID \| None` | `None` |
| `template_clear` | `bool` | `False` |

#### WorkforceAnnouncementPublishIn

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |

#### WorkforceAnnouncementArchiveIn

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |

#### WorkforceAnnouncementAcknowledgeIn

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |

#### WorkforceAnnouncementReceiptOut

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `read_at` | `datetime \| None` | `None` |
| `acknowledged_at` | `datetime \| None` | `None` |

#### WorkforceAnnouncementOut

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `template_id` | `uuid.UUID \| None` | `None` |
| `title` | `str` | `Required` |
| `body` | `str` | `Required` |
| `priority` | `str` | `Required` |
| `status` | `str` | `Required` |
| `published_at` | `datetime \| None` | `None` |
| `scheduled_publish_at` | `datetime \| None` | `None` |
| `expires_at` | `date \| None` | `None` |
| `pinned` | `bool` | `Required` |
| `acknowledgement_required` | `bool` | `Required` |
| `audience_kind` | `str` | `Required` |
| `audience_ids` | `list[str] \| None` | `None` |
| `attachments_json` | `list[dict[str, Any]] \| None` | `None` |
| `send_email_on_publish` | `bool` | `Required` |
| `automation_dedupe_key` | `str \| None` | `None` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |
| `my_receipt` | `WorkforceAnnouncementReceiptOut \| None` | `None` |

#### WorkforceAnnouncementDetailOut

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `WorkforceAnnouncementOut`.

| Field | Type | Default / validation |
| --- | --- | --- |

#### WorkforceAnnouncementDeliveryOut

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `announcement_id` | `uuid.UUID` | `Required` |
| `channel` | `str` | `Required` |
| `user_id` | `uuid.UUID \| None` | `None` |
| `recipient_email` | `str` | `Required` |
| `status` | `str` | `Required` |
| `error` | `str \| None` | `None` |
| `outbox_event_id` | `uuid.UUID \| None` | `None` |
| `sent_at` | `datetime \| None` | `None` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |
| `outbox_status` | `str \| None` | `None` |
| `outbox_attempts` | `int \| None` | `None` |
| `outbox_last_error` | `str \| None` | `None` |

#### WorkforceAnnouncementDeliveryListOut

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `items` | `list[WorkforceAnnouncementDeliveryOut]` | `Required` |
| `total` | `int` | `Required` |
| `page` | `int` | `Required` |
| `page_size` | `int` | `Required` |

#### WorkforceAnnouncementAttachmentUploadOut

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `name` | `str` | `Required` |
| `url` | `str` | `Required` |
| `content_type` | `str` | `Required` |
| `size_bytes` | `int` | `Required` |

#### WorkforceAutomationKeysOut

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `keys` | `list[str]` | `Required` |

#### WorkforceAnnouncementTemplateCreateIn

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `name` | `str` | `Field(min_length=1, max_length=200)` |
| `body_template` | `str` | `Field(min_length=1)` |
| `code` | `str \| None` | `Field(default=None, max_length=64)` |
| `description` | `str \| None` | `Field(default=None, max_length=500)` |
| `automation_key` | `str \| None` | `Field(default=None, max_length=64)` |

#### WorkforceAnnouncementTemplateUpdateIn

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `name` | `str \| None` | `Field(default=None, min_length=1, max_length=200)` |
| `body_template` | `str \| None` | `Field(default=None, min_length=1)` |
| `code` | `str \| None` | `Field(default=None, max_length=64)` |
| `code_clear` | `bool` | `False` |
| `description` | `str \| None` | `Field(default=None, max_length=500)` |
| `description_clear` | `bool` | `False` |
| `automation_key` | `str \| None` | `Field(default=None, max_length=64)` |
| `automation_clear` | `bool` | `False` |
| `is_active` | `bool \| None` | `None` |

#### WorkforceAnnouncementTemplateOut

Source: [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `name` | `str` | `Required` |
| `code` | `str \| None` | `None` |
| `description` | `str \| None` | `None` |
| `body_template` | `str` | `Required` |
| `automation_key` | `str \| None` | `None` |
| `is_active` | `bool` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforceShiftCreateIn

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `name` | `str` | `Field(min_length=1, max_length=120)` |
| `start_time` | `time` | `Required` |
| `end_time` | `time` | `Required` |
| `grace_minutes` | `int` | `Field(default=5, ge=0, le=240)` |
| `is_active` | `bool` | `True` |

#### WorkforceShiftUpdateIn

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `name` | `str \| None` | `Field(default=None, min_length=1, max_length=120)` |
| `start_time` | `time \| None` | `None` |
| `end_time` | `time \| None` | `None` |
| `grace_minutes` | `int \| None` | `Field(default=None, ge=0, le=240)` |
| `is_active` | `bool \| None` | `None` |

#### WorkforceShiftOut

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `name` | `str` | `Required` |
| `start_time` | `time` | `Required` |
| `end_time` | `time` | `Required` |
| `grace_minutes` | `int` | `Required` |
| `is_active` | `bool` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforceShiftAssignmentCreateIn

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `employee_id` | `uuid.UUID` | `Required` |
| `shift_id` | `uuid.UUID` | `Required` |
| `effective_from` | `date` | `Required` |
| `effective_to` | `date \| None` | `None` |

#### WorkforceShiftAssignmentOut

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `employee_id` | `uuid.UUID` | `Required` |
| `shift_id` | `uuid.UUID` | `Required` |
| `effective_from` | `date` | `Required` |
| `effective_to` | `date \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforceAttendanceClockInIn

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `employee_id` | `uuid.UUID` | `Required` |
| `at` | `datetime \| None` | `None` |

#### WorkforceAttendanceClockOutIn

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `employee_id` | `uuid.UUID` | `Required` |
| `at` | `datetime \| None` | `None` |

#### WorkforceAttendanceManualIn

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `employee_id` | `uuid.UUID` | `Required` |
| `work_date` | `date` | `Required` |
| `status` | `str` | `Field(default='PRESENT', max_length=16)` |
| `clock_in_at` | `datetime \| None` | `None` |
| `clock_out_at` | `datetime \| None` | `None` |
| `notes` | `str \| None` | `Field(default=None, max_length=500)` |

#### WorkforceAttendanceOut

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `employee_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `work_date` | `date` | `Required` |
| `status` | `str` | `Required` |
| `source` | `str` | `Required` |
| `shift_id` | `uuid.UUID \| None` | `Required` |
| `shift_assignment_id` | `uuid.UUID \| None` | `Required` |
| `clock_in_at` | `datetime \| None` | `Required` |
| `clock_out_at` | `datetime \| None` | `Required` |
| `is_late` | `bool` | `Required` |
| `minutes_late` | `int` | `Required` |
| `missing_checkout` | `bool` | `Required` |
| `worked_minutes` | `int` | `Required` |
| `overtime_minutes` | `int` | `Required` |
| `payable_hours` | `Decimal` | `Required` |
| `notes` | `str \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforceAttendanceDailyOut

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `date` | `date` | `Required` |
| `items` | `list[WorkforceAttendanceOut]` | `Required` |

#### WorkforceAttendanceCalendarDayOut

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `date` | `date` | `Required` |
| `totals` | `dict[str, int]` | `Required` |
| `late_count` | `int` | `Required` |
| `missing_checkout_count` | `int` | `Required` |

#### WorkforceAttendanceCalendarOut

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `month` | `str` | `Required` |
| `days` | `list[WorkforceAttendanceCalendarDayOut]` | `Required` |

#### WorkforceAttendanceCorrectionRequestIn

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `attendance_record_id` | `uuid.UUID` | `Required` |
| `reason` | `str` | `Field(min_length=3, max_length=500)` |
| `proposed_clock_in_at` | `datetime \| None` | `None` |
| `proposed_clock_out_at` | `datetime \| None` | `None` |
| `proposed_status` | `str \| None` | `Field(default=None, max_length=16)` |

#### WorkforceAttendanceCorrectionReviewIn

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `status` | `str` | `Field(..., max_length=16)` |
| `reviewer_note` | `str \| None` | `Field(default=None, max_length=500)` |

#### WorkforceAttendanceCorrectionOut

Source: [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `employee_id` | `uuid.UUID` | `Required` |
| `attendance_record_id` | `uuid.UUID` | `Required` |
| `requested_by_user_id` | `uuid.UUID` | `Required` |
| `reviewed_by_user_id` | `uuid.UUID \| None` | `Required` |
| `status` | `str` | `Required` |
| `reason` | `str` | `Required` |
| `proposed_clock_in_at` | `datetime \| None` | `Required` |
| `proposed_clock_out_at` | `datetime \| None` | `Required` |
| `proposed_status` | `str \| None` | `Required` |
| `reviewer_note` | `str \| None` | `Required` |
| `reviewed_at` | `datetime \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforcePolicyCreateIn

Source: [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `code` | `str` | `Field(min_length=1, max_length=64)` |
| `title` | `str` | `Field(min_length=1, max_length=240)` |
| `body` | `str` | `Field(min_length=1)` |
| `requires_ack` | `bool` | `True` |
| `publish_now` | `bool` | `False` |
| `is_active` | `bool` | `True` |

#### WorkforcePolicyOut

Source: [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `code` | `str` | `Required` |
| `title` | `str` | `Required` |
| `body` | `str` | `Required` |
| `version` | `int` | `Required` |
| `requires_ack` | `bool` | `Required` |
| `is_active` | `bool` | `Required` |
| `published_at` | `datetime \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforcePolicyPublishIn

Source: [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |

#### WorkforcePolicyAckCreateIn

Source: [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `employee_id` | `uuid.UUID` | `Required` |

#### WorkforcePolicyAckOut

Source: [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `policy_id` | `uuid.UUID` | `Required` |
| `employee_id` | `uuid.UUID` | `Required` |
| `acknowledged_at` | `datetime` | `Required` |
| `acknowledged_by_user_id` | `uuid.UUID` | `Required` |

#### WorkforceDocumentOut

Source: [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `employee_id` | `uuid.UUID \| None` | `Required` |
| `policy_id` | `uuid.UUID \| None` | `Required` |
| `name` | `str` | `Required` |
| `content_type` | `str` | `Required` |
| `size_bytes` | `int` | `Required` |
| `object_key` | `str` | `Required` |
| `url` | `str` | `Required` |
| `is_active` | `bool` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforceDocumentDeactivateIn

Source: [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |

#### WorkforceDocumentUploadOut

Source: [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `name` | `str` | `Required` |
| `url` | `str` | `Required` |
| `content_type` | `str` | `Required` |
| `size_bytes` | `int` | `Required` |
| `object_key` | `str` | `Required` |

#### WorkforceChecklistItemCreateIn

Source: [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `employee_id` | `uuid.UUID` | `Required` |
| `kind` | `str` | `Field(max_length=16)` |
| `title` | `str` | `Field(min_length=1, max_length=240)` |
| `details` | `str \| None` | `Field(default=None, max_length=1000)` |
| `due_date` | `date \| None` | `None` |

#### WorkforceChecklistItemOut

Source: [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `employee_id` | `uuid.UUID` | `Required` |
| `kind` | `str` | `Required` |
| `title` | `str` | `Required` |
| `details` | `str \| None` | `Required` |
| `due_date` | `date \| None` | `Required` |
| `is_done` | `bool` | `Required` |
| `completed_at` | `datetime \| None` | `Required` |
| `completed_by_user_id` | `uuid.UUID \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforceChecklistDoneIn

Source: [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `is_done` | `bool` | `Required` |

#### WorkforceDashboardIntelOut

Source: [backend/app/domain/schemas/workforce_intelligence.py](backend/app/domain/schemas/workforce_intelligence.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `as_of` | `date` | `Required` |
| `present_today` | `int` | `0` |
| `absent_today` | `int` | `0` |
| `late_today` | `int` | `0` |
| `missing_checkout_today` | `int` | `0` |
| `pending_leave_requests` | `int` | `0` |
| `payroll_due_periods` | `int` | `0` |
| `unpaid_payroll_entries` | `int` | `0` |
| `contract_expiring_soon` | `int` | `0` |
| `probation_ending_soon` | `int` | `0` |
| `unacknowledged_announcements` | `int` | `0` |
| `top_risks` | `list[str]` | `Field(default_factory=list, max_length=10)` |

#### WorkforceAttendanceSummaryOut

Source: [backend/app/domain/schemas/workforce_intelligence.py](backend/app/domain/schemas/workforce_intelligence.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `present_days` | `int` | `0` |
| `absent_days` | `int` | `0` |
| `late_incidents` | `int` | `0` |
| `missing_checkouts` | `int` | `0` |
| `total_records` | `int` | `0` |

#### WorkforceLeaveSummaryOut

Source: [backend/app/domain/schemas/workforce_intelligence.py](backend/app/domain/schemas/workforce_intelligence.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `pending_requests` | `int` | `0` |
| `approved_requests_overlapping` | `int` | `0` |

#### WorkforcePayrollSummaryOut

Source: [backend/app/domain/schemas/workforce_intelligence.py](backend/app/domain/schemas/workforce_intelligence.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `periods_overlapping` | `int` | `0` |
| `total_net_pay_in_range` | `str` | `'0.00'` |
| `unpaid_entries_in_overlapping_periods` | `int` | `0` |

#### WorkforceDepartmentHeadcountOut

Source: [backend/app/domain/schemas/workforce_intelligence.py](backend/app/domain/schemas/workforce_intelligence.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `department_id` | `uuid.UUID \| None` | `None` |
| `department_name` | `str` | `Required` |
| `headcount` | `int` | `0` |

#### WorkforceLaborCostPeriodOut

Source: [backend/app/domain/schemas/workforce_intelligence.py](backend/app/domain/schemas/workforce_intelligence.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `payroll_period_id` | `uuid.UUID` | `Required` |
| `period_start` | `date` | `Required` |
| `period_end` | `date` | `Required` |
| `total_net_pay` | `str` | `'0.00'` |

#### WorkforceReportsSummaryOut

Source: [backend/app/domain/schemas/workforce_intelligence.py](backend/app/domain/schemas/workforce_intelligence.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID` | `Required` |
| `from_date` | `date` | `Required` |
| `to_date` | `date` | `Required` |
| `attendance` | `WorkforceAttendanceSummaryOut` | `Required` |
| `leave` | `WorkforceLeaveSummaryOut` | `Required` |
| `payroll` | `WorkforcePayrollSummaryOut` | `Required` |
| `department_headcount` | `list[WorkforceDepartmentHeadcountOut]` | `Field(default_factory=list)` |
| `labor_cost_by_period` | `list[WorkforceLaborCostPeriodOut]` | `Field(default_factory=list)` |
| `summary_lines` | `list[str]` | `Field(default_factory=list, max_length=20)` |

#### WorkforceLeaveTypeCreateIn

Source: [backend/app/domain/schemas/workforce_leave.py](backend/app/domain/schemas/workforce_leave.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `name` | `str` | `Field(min_length=1, max_length=120)` |
| `code` | `str \| None` | `Field(default=None, max_length=40)` |
| `is_paid` | `bool` | `True` |
| `requires_approval` | `bool` | `True` |
| `is_active` | `bool` | `True` |

#### WorkforceLeaveTypeUpdateIn

Source: [backend/app/domain/schemas/workforce_leave.py](backend/app/domain/schemas/workforce_leave.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `name` | `str \| None` | `Field(default=None, min_length=1, max_length=120)` |
| `code` | `str \| None` | `Field(default=None, max_length=40)` |
| `is_paid` | `bool \| None` | `None` |
| `requires_approval` | `bool \| None` | `None` |
| `is_active` | `bool \| None` | `None` |

#### WorkforceLeaveTypeOut

Source: [backend/app/domain/schemas/workforce_leave.py](backend/app/domain/schemas/workforce_leave.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `name` | `str` | `Required` |
| `code` | `str \| None` | `Required` |
| `is_paid` | `bool` | `Required` |
| `requires_approval` | `bool` | `Required` |
| `is_active` | `bool` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforceLeaveBalanceOut

Source: [backend/app/domain/schemas/workforce_leave.py](backend/app/domain/schemas/workforce_leave.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `employee_id` | `uuid.UUID` | `Required` |
| `leave_type_id` | `uuid.UUID` | `Required` |
| `year` | `int` | `Required` |
| `allocated_days` | `Decimal` | `Required` |
| `used_days` | `Decimal` | `Required` |
| `pending_days` | `Decimal` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforceLeaveBalanceAllocateIn

Source: [backend/app/domain/schemas/workforce_leave.py](backend/app/domain/schemas/workforce_leave.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `employee_id` | `uuid.UUID` | `Required` |
| `leave_type_id` | `uuid.UUID` | `Required` |
| `year` | `int` | `Field(..., ge=2000, le=2100)` |
| `allocated_days` | `Decimal` | `Field(..., ge=0)` |

#### WorkforceLeaveRequestCreateIn

Source: [backend/app/domain/schemas/workforce_leave.py](backend/app/domain/schemas/workforce_leave.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `employee_id` | `uuid.UUID` | `Required` |
| `leave_type_id` | `uuid.UUID` | `Required` |
| `start_date` | `date` | `Required` |
| `end_date` | `date` | `Required` |
| `days` | `Decimal` | `Field(default=Decimal('1'), ge=Decimal('0.5'))` |
| `reason` | `str \| None` | `Field(default=None, max_length=500)` |

#### WorkforceLeaveRequestOut

Source: [backend/app/domain/schemas/workforce_leave.py](backend/app/domain/schemas/workforce_leave.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `employee_id` | `uuid.UUID` | `Required` |
| `leave_type_id` | `uuid.UUID` | `Required` |
| `start_date` | `date` | `Required` |
| `end_date` | `date` | `Required` |
| `days` | `Decimal` | `Required` |
| `status` | `str` | `Required` |
| `reason` | `str \| None` | `Required` |
| `reviewed_by_user_id` | `uuid.UUID \| None` | `Required` |
| `reviewed_at` | `datetime \| None` | `Required` |
| `reviewer_note` | `str \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforceLeaveRequestDecisionIn

Source: [backend/app/domain/schemas/workforce_leave.py](backend/app/domain/schemas/workforce_leave.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `status` | `str` | `Field(..., max_length=16)` |
| `reviewer_note` | `str \| None` | `Field(default=None, max_length=500)` |

#### WorkforcePayrollPeriodCreateIn

Source: [backend/app/domain/schemas/workforce_payroll.py](backend/app/domain/schemas/workforce_payroll.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `start_date` | `date` | `Required` |
| `end_date` | `date` | `Required` |

#### WorkforcePayrollPeriodOut

Source: [backend/app/domain/schemas/workforce_payroll.py](backend/app/domain/schemas/workforce_payroll.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `start_date` | `date` | `Required` |
| `end_date` | `date` | `Required` |
| `status` | `str` | `Required` |
| `approved_by_user_id` | `uuid.UUID \| None` | `Required` |
| `approved_at` | `datetime \| None` | `Required` |
| `paid_by_user_id` | `uuid.UUID \| None` | `Required` |
| `paid_at` | `datetime \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforcePayrollGenerateDraftIn

Source: [backend/app/domain/schemas/workforce_payroll.py](backend/app/domain/schemas/workforce_payroll.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `payroll_period_id` | `uuid.UUID` | `Required` |
| `include_inactive_employees` | `bool` | `False` |
| `overtime_multiplier` | `Decimal` | `Field(default=Decimal('1.5'), ge=Decimal('1.0'), le=Decimal('5.0'))` |

#### WorkforcePayrollPeriodActionIn

Source: [backend/app/domain/schemas/workforce_payroll.py](backend/app/domain/schemas/workforce_payroll.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |

#### WorkforcePayrollEntryOut

Source: [backend/app/domain/schemas/workforce_payroll.py](backend/app/domain/schemas/workforce_payroll.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `payroll_period_id` | `uuid.UUID` | `Required` |
| `employee_id` | `uuid.UUID` | `Required` |
| `salary_type` | `str` | `Required` |
| `base_salary` | `Decimal \| None` | `Required` |
| `hourly_rate` | `Decimal \| None` | `Required` |
| `overtime_multiplier` | `Decimal \| None` | `Required` |
| `worked_minutes` | `int` | `Required` |
| `overtime_minutes` | `int` | `Required` |
| `payable_hours` | `Decimal \| None` | `Required` |
| `unpaid_leave_deduction` | `Decimal \| None` | `Required` |
| `gross_pay` | `Decimal \| None` | `Required` |
| `adjustments_total` | `Decimal \| None` | `Required` |
| `net_pay` | `Decimal \| None` | `Required` |
| `status` | `str` | `Required` |
| `is_locked` | `bool` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforcePayrollAdjustmentCreateIn

Source: [backend/app/domain/schemas/workforce_payroll.py](backend/app/domain/schemas/workforce_payroll.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `org_id` | `uuid.UUID \| None` | `None` |
| `payroll_period_id` | `uuid.UUID` | `Required` |
| `payroll_entry_id` | `uuid.UUID` | `Required` |
| `employee_id` | `uuid.UUID` | `Required` |
| `kind` | `str` | `Field(..., max_length=20)` |
| `amount` | `Decimal` | `Required` |
| `label` | `str \| None` | `Field(default=None, max_length=200)` |
| `notes` | `str \| None` | `Field(default=None, max_length=500)` |

#### WorkforcePayrollAdjustmentOut

Source: [backend/app/domain/schemas/workforce_payroll.py](backend/app/domain/schemas/workforce_payroll.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `id` | `uuid.UUID` | `Required` |
| `org_id` | `uuid.UUID` | `Required` |
| `created_by_user_id` | `uuid.UUID` | `Required` |
| `payroll_period_id` | `uuid.UUID` | `Required` |
| `payroll_entry_id` | `uuid.UUID` | `Required` |
| `employee_id` | `uuid.UUID` | `Required` |
| `kind` | `str` | `Required` |
| `amount` | `Decimal \| None` | `Required` |
| `label` | `str \| None` | `Required` |
| `notes` | `str \| None` | `Required` |
| `created_at` | `datetime` | `Required` |
| `updated_at` | `datetime` | `Required` |

#### WorkforcePayslipPreviewOut

Source: [backend/app/domain/schemas/workforce_payroll.py](backend/app/domain/schemas/workforce_payroll.py). Bases: `BaseModel`.

| Field | Type | Default / validation |
| --- | --- | --- |
| `entry` | `WorkforcePayrollEntryOut` | `Required` |
| `adjustments` | `list[WorkforcePayrollAdjustmentOut]` | `Required` |
| `period` | `WorkforcePayrollPeriodOut` | `Required` |

### E. Command, service, repository, adapter and task reference

#### Frontend npm commands

| Command | Exact script |
| --- | --- |
| `npm run dev` | `next dev` |
| `npm run build` | `next build` |
| `npm run analyze` | `cross-env ANALYZE=true next build` |
| `npm run start` | `next start` |
| `npm run lint` | `next lint` |
| `npm run e2e` | `playwright test` |
| `npm run e2e:full` | `playwright test` |
| `npm run e2e:smoke` | `playwright test e2e/responsive-mobile.spec.ts e2e/responsive-smoke.spec.ts e2e/onboarding-workspace.spec.ts e2e/auth-confirm-ui.spec.ts e2e/rbac-viewer-api.spec.ts e2e/rbac-viewer-settings-api.spec.ts e2e/stripe-reconciliation-invalid-range.spec.ts e2e/workforce-payroll.spec.ts e2e/workforce-leave.spec.ts e2e/workforce-attendance.spec.ts` |
| `npm run e2e:workforce` | `playwright test e2e/workforce-attendance.spec.ts e2e/workforce-leave.spec.ts e2e/workforce-payroll.spec.ts e2e/workforce-hr-admin.spec.ts e2e/workforce-phase7-intelligence.spec.ts` |
| `npm run e2e:workforce:ci` | `cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer npm run e2e:workforce` |
| `npm run e2e:workforce:responsive:ci` | `cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer playwright test e2e/workforce-responsive.spec.ts` |
| `npm run e2e:workforce:rbac:ci` | `cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer playwright test e2e/workforce-rbac-negative.spec.ts` |
| `npm run e2e:workforce:onoff:ci` | `cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer playwright test e2e/workforce-onboarding-offboarding.spec.ts` |
| `npm run e2e:workforce:comms-failure:ci` | `cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer playwright test e2e/workforce-communications-failure-states.spec.ts` |
| `npm run e2e:workforce:activity-failure:ci` | `cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer playwright test e2e/workforce-activity-failure-retry.spec.ts` |
| `npm run e2e:workforce:mobile-dense:ci` | `cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer playwright test e2e/workforce-mobile-dense-interactions.spec.ts` |
| `npm run e2e:workforce:states:ci` | `cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer playwright test e2e/workforce-state-matrix.spec.ts` |
| `npm run e2e:workforce:gate:ci` | `npm run e2e:workforce:ci && npm run e2e:workforce:responsive:ci && npm run e2e:workforce:rbac:ci && npm run e2e:workforce:onoff:ci && npm run e2e:workforce:comms-failure:ci && npm run e2e:workforce:activity-failure:ci && npm run e2e:workforce:mobile-dense:ci && npm run e2e:workforce:states:ci` |
| `npm run e2e:payroll-workflow` | `playwright test e2e/workforce-payroll-workflow.spec.ts` |
| `npm run e2e:leave-workflow` | `playwright test e2e/workforce-leave-workflow.spec.ts` |
| `npm run e2e:smoke:ci` | `cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer npm run e2e:smoke` |
| `npm run e2e:smoke:ci:full` | `cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer npm run e2e:smoke && cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer npm run e2e:payroll-workflow && cross-env E2E_USE_EXTERNAL_BASE_URL=1 E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 E2E_AUTH_MODE=bearer npm run e2e:leave-workflow` |
| `npm run e2e:sse` | `cross-env E2E_SSE=1 playwright test e2e/sse-fallback.spec.ts` |
| `npm run e2e:integrations` | `playwright test e2e/plaid-integration.spec.ts e2e/stripe-integration.spec.ts` |
| `npm run e2e:headed` | `playwright test --headed` |
| `npm run e2e:cookie` | `cross-env E2E_AUTH_MODE=cookie playwright test` |
| `npm run e2e:visual` | `cross-env E2E_VISUAL=1 playwright test e2e/visual.spec.ts` |
| `npm run e2e:visual:update` | `cross-env E2E_VISUAL=1 playwright test e2e/visual.spec.ts --update-snapshots` |
| `npm run format` | `prettier --write .` |
| `npm run check` | `npm run lint && npm run build` |

#### Complete dependency declarations

| Package group | Declaration |
| --- | --- |
| Backend runtime | `fastapi>=0.115` |
| Backend runtime | `uvicorn[standard]>=0.30` |
| Backend runtime | `pydantic>=2.8` |
| Backend runtime | `pydantic-settings>=2.4` |
| Backend runtime | `sqlalchemy[asyncio]>=2.0` |
| Backend runtime | `alembic>=1.13` |
| Backend runtime | `asyncpg>=0.29` |
| Backend runtime | `psycopg2-binary>=2.9` |
| Backend runtime | `argon2-cffi>=23.1` |
| Backend runtime | `python-jose[cryptography]>=3.3` |
| Backend runtime | `redis>=5.0` |
| Backend runtime | `celery[redis]>=5.4` |
| Backend runtime | `boto3>=1.34` |
| Backend runtime | `python-multipart>=0.0.9` |
| Backend runtime | `email-validator>=2.2` |
| Backend runtime | `reportlab>=4.2` |
| Backend runtime | `httpx>=0.27` |
| Backend runtime | `resend>=2.13` |
| Backend runtime | `structlog>=24.4` |
| Backend runtime | `sentry-sdk>=2.13` |
| Backend runtime | `stripe>=11.6` |
| Backend dev | `pytest>=8.3` |
| Backend dev | `pytest-asyncio>=0.24` |
| Backend dev | `pytest-cov>=5.0` |
| Backend dev | `ruff>=0.6` |
| Backend dev | `black>=24.8` |
| Backend dev | `mypy>=1.11` |
| dependencies | `@radix-ui/react-dialog ^1.1.15` |
| dependencies | `@radix-ui/react-dropdown-menu ^2.1.16` |
| dependencies | `@radix-ui/react-label ^2.1.8` |
| dependencies | `@radix-ui/react-select ^2.2.6` |
| dependencies | `@radix-ui/react-slot ^1.2.4` |
| dependencies | `@radix-ui/react-tabs ^1.1.13` |
| dependencies | `@radix-ui/react-toast ^1.2.15` |
| dependencies | `@radix-ui/react-tooltip ^1.2.8` |
| dependencies | `@tanstack/react-query ^5.90.21` |
| dependencies | `@tanstack/react-table ^8.21.3` |
| dependencies | `@tanstack/react-virtual ^3.13.19` |
| dependencies | `class-variance-authority ^0.7.1` |
| dependencies | `clsx ^2.1.1` |
| dependencies | `framer-motion ^12.35.0` |
| dependencies | `lucide-react ^0.577.0` |
| dependencies | `next 15.5.12` |
| dependencies | `next-themes ^0.4.6` |
| dependencies | `react 18.3.1` |
| dependencies | `react-dom 18.3.1` |
| dependencies | `recharts 2.13.0` |
| dependencies | `tailwind-merge ^3.5.0` |
| dependencies | `zod ^4.3.6` |
| dependencies | `zustand ^5.0.11` |
| devDependencies | `@playwright/test ^1.58.2` |
| devDependencies | `@tailwindcss/postcss ^4.2.1` |
| devDependencies | `@types/node 20.16.5` |
| devDependencies | `@types/react 18.3.5` |
| devDependencies | `autoprefixer ^10.4.20` |
| devDependencies | `cross-env ^10.1.0` |
| devDependencies | `eslint 9.11.1` |
| devDependencies | `eslint-config-next 15.5.12` |
| devDependencies | `postcss ^8.4.49` |
| devDependencies | `prettier ^3.8.1` |
| devDependencies | `prettier-plugin-tailwindcss ^0.7.2` |
| devDependencies | `tailwindcss ^3.4.17` |
| devDependencies | `typescript 5.6.2` |

#### Python command-line options

Options for [scripts/loadtest/bootstrap_multi_org_perf.py](scripts/loadtest/bootstrap_multi_org_perf.py):

| Argument | Default / type / required / help |
| --- | --- |
| `'--base-url'` | `default='http://localhost:8000/api/v1'` |
| `'--org-count'` | `type=int, default=10` |
| `'--org-name-prefix'` | `default='Perf Org'` |
| `'--password'` | `default='Password123!'` |

Options for [scripts/loadtest/evaluate_perf_gates.py](scripts/loadtest/evaluate_perf_gates.py):

| Argument | Default / type / required / help |
| --- | --- |
| `'--slo'` | `required=True, type=Path` |
| `'--read-pass-1'` | `required=True, type=Path` |
| `'--read-pass-2'` | `required=True, type=Path` |
| `'--runtime-observability'` | `required=True, type=Path` |
| `'--out-json'` | `required=True, type=Path` |
| `'--out-md'` | `required=True, type=Path` |

Options for [scripts/ops/secret_hygiene_audit.py](scripts/ops/secret_hygiene_audit.py):

| Argument | Default / type / required / help |
| --- | --- |
| `'--root'` | `default='.'` |
| `'--env-file'` | `default='.env.example'` |
| `'--out-json'` | `default='secret-hygiene-report.json'` |
| `'--out-md'` | `default='secret-hygiene-report.md'` |

Options for [scripts/ops/verify_ai_live_mode.py](scripts/ops/verify_ai_live_mode.py):

| Argument | Default / type / required / help |
| --- | --- |
| `'--api-base-url'` | `default='http://localhost:8000/api/v1'` |
| `'--database-url'` | `default=os.getenv('DATABASE_URL', 'postgresql://ai_coo:ai_coo@localhost:5432/ai_coo')` |
| `'--email'` | `default=''` |
| `'--password'` | `default='Password123!'` |
| `'--org-name'` | `default='AI Live Verify Org'` |
| `'--expected-provider'` | `default='openai'` |
| `'--live-check'` | `action='store_true'` |
| `'--verify-fallback-test'` | `action='store_true'` |
| `'--fallback-test-path'` | `default='backend/app/tests/test_ai_service.py::test_ai_service_falls_back_on_provider_error'` |
| `'--out-json'` | `default='ai-live-mode-report.json'` |

Options for [scripts/seed_load_dataset.py](scripts/seed_load_dataset.py):

| Argument | Default / type / required / help |
| --- | --- |
| `'--org-id'` | `action='append', help='Target organization UUID (repeatable)'` |
| `'--org-ids-file'` | `help='Optional JSON/TXT file with organization UUIDs (JSON list or one UUID per line)'` |
| `'--created-by'` | `required=True, help='User UUID for created_by'` |
| `'--months'` | `type=int, default=12, help='Number of months to span (default: 12)'` |
| `'--rows'` | `type=int, default=50000, help='Number of transactions to generate per org'` |
| `'--chunk-size'` | `type=int, default=5000, help='Insert chunk size'` |
| `'--seed'` | `type=int, default=42, help='Random seed'` |

Options for [scripts/smoke_mvp.py](scripts/smoke_mvp.py):

| Argument | Default / type / required / help |
| --- | --- |
| `'--base-url'` | `default='http://localhost:8000/api/v1'` |
| `'--auth-mode'` | `choices=['bearer', 'cookie'], default='bearer'` |
| `'--csrf-cookie-name'` | `default='ai_coo_csrf_token'` |
| `'--csrf-header-name'` | `default='X-CSRF-Token'` |
| `'--email'` | `default=os.getenv('SMOKE_USER_EMAIL') or os.getenv('E2E_USER_EMAIL')` |
| `'--password'` | `default=os.getenv('SMOKE_USER_PASSWORD') or os.getenv('E2E_USER_PASSWORD')` |
| `'--org-id'` | `default=os.getenv('SMOKE_ORG_ID') or os.getenv('E2E_ORG_ID')` |
| `'--csv'` | `default=str(Path(__file__).resolve().parents[1] / 'shared' / 'demo' / 'transactions_6months.csv')` |

Options for [scripts/smoke_workforce_intelligence.py](scripts/smoke_workforce_intelligence.py):

| Argument | Default / type / required / help |
| --- | --- |
| `'--base-url'` | `default=os.getenv('SMOKE_BASE_URL', 'http://127.0.0.1:8000/api/v1')` |
| `'--auth-mode'` | `default=os.getenv('SMOKE_AUTH_MODE', 'bearer'), choices=['bearer', 'cookie']` |
| `'--csrf-cookie-name'` | `default=os.getenv('SMOKE_CSRF_COOKIE_NAME', 'ai_coo_csrf_token')` |
| `'--csrf-header-name'` | `default=os.getenv('SMOKE_CSRF_HEADER_NAME', 'X-CSRF-Token')` |
| `'--seeded-email'` | `default=os.getenv('SMOKE_USER_EMAIL')` |
| `'--seeded-password'` | `default=os.getenv('SMOKE_USER_PASSWORD')` |
| `'--seeded-org-id'` | `default=os.getenv('SMOKE_ORG_ID')` |
| `'--as-of'` | `default=os.getenv('SMOKE_AS_OF')` |

Options for [scripts/verify_runtime.py](scripts/verify_runtime.py):

| Argument | Default / type / required / help |
| --- | --- |
| `'--api-base-url'` | `default='http://localhost:8000/api/v1'` |
| `'--frontend-base-url'` | `default='http://localhost:3000'` |
| `'--health-timeout-sec'` | `type=int, default=120` |
| `'--skip-backend-tests'` | `action='store_true'` |
| `'--skip-e2e'` | `action='store_true'` |
| `'--with-visual'` | `action='store_true'` |

#### k6 environment controls

- [scripts/loadtest/_shared.js](scripts/loadtest/_shared.js) — `return __ENV.WEEK_START || new Date().toISOString().slice(0, 10);`

- [scripts/loadtest/k6-inventory-churn.js](scripts/loadtest/k6-inventory-churn.js) — `const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";`; `rate: Number(__ENV.RATE || 6),`; `duration: __ENV.DURATION || "90s",`; `preAllocatedVUs: Number(__ENV.PREALLOCATED_VUS || 12),`; `maxVUs: Number(__ENV.MAX_VUS || 80),`; `sleep(Number(__ENV.SLEEP_SECONDS || 0.2));`; `sleep(Number(__ENV.SLEEP_SECONDS || 0.35));`

- [scripts/loadtest/k6-many-org-dashboard.js](scripts/loadtest/k6-many-org-dashboard.js) — `const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";`; `vus: Number(__ENV.VUS || 40),`; `duration: __ENV.DURATION || "2m",`; `sleep(Number(__ENV.SLEEP_SECONDS || 1));`

- [scripts/loadtest/k6-mixed-churn.js](scripts/loadtest/k6-mixed-churn.js) — `const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";`; `rate: Number(__ENV.RATE || 15),`; `duration: __ENV.DURATION || "90s",`; `preAllocatedVUs: Number(__ENV.PREALLOCATED_VUS || 25),`; `maxVUs: Number(__ENV.MAX_VUS || 80),`; `sleep(Number(__ENV.SLEEP_SECONDS || 0.5));`

- [scripts/loadtest/k6-read-hotpaths.js](scripts/loadtest/k6-read-hotpaths.js) — `const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";`; `const runtimeMetricsEnabled = String(__ENV.RUNTIME_METRICS_ENABLED || "false").toLowerCase() !== "false";`; `const runtimeMetricsEveryN = Math.max(1, Number(__ENV.RUNTIME_METRICS_EVERY_N || 1));`; `rate: Number(__ENV.RATE || 13),`; `duration: __ENV.DURATION || "90s",`; `preAllocatedVUs: Number(__ENV.PREALLOCATED_VUS || 30),`; `maxVUs: Number(__ENV.MAX_VUS || 120),`; `sleep(Number(__ENV.SLEEP_SECONDS || 0.3));`

- [scripts/loadtest/k6-report-burst.js](scripts/loadtest/k6-report-burst.js) — `const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";`; `{ duration: "20s", target: Number(__ENV.BURST_TARGET_VUS || 30) },`; `{ duration: "60s", target: Number(__ENV.BURST_TARGET_VUS || 30) },`; `sleep(Number(__ENV.SLEEP_SECONDS || 0.5));`

- [scripts/loadtest/k6-runtime-observability.js](scripts/loadtest/k6-runtime-observability.js) — `const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";`; `rate: Number(__ENV.RATE || 2),`; `duration: __ENV.DURATION || "90s",`; `preAllocatedVUs: Number(__ENV.PREALLOCATED_VUS || 5),`; `maxVUs: Number(__ENV.MAX_VUS || 20),`; `sleep(Number(__ENV.SLEEP_SECONDS || 0.5));`

- [scripts/loadtest/k6-smoke.js](scripts/loadtest/k6-smoke.js) — `const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";`; `const accessToken = __ENV.ACCESS_TOKEN;`; `const orgId = __ENV.ORG_ID;`; `const fromDate = __ENV.FROM_DATE;`; `const toDate = __ENV.TO_DATE;`

- [scripts/loadtest/k6-write-heavy.js](scripts/loadtest/k6-write-heavy.js) — `const baseUrl = __ENV.BASE_URL || "http://localhost:8000/api/v1";`; `rate: Number(__ENV.RATE || 10),`; `duration: __ENV.DURATION || "90s",`; `preAllocatedVUs: Number(__ENV.PREALLOCATED_VUS || 20),`; `maxVUs: Number(__ENV.MAX_VUS || 120),`; `sleep(Number(__ENV.SLEEP_SECONDS || 0.4));`

#### Implementation symbols

Functions and class methods include private helpers, exact signatures/defaults and source links. API handlers are indexed above; remaining API helper signatures also appear here.

#### [backend/app/__init__.py](backend/app/__init__.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/api/__init__.py](backend/app/api/__init__.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/api/deps.py](backend/app/api/deps.py)

- Class `OrgContext`
- `get_current_user(creds: HTTPAuthorizationCredentials | None=Depends(bearer), request: Request=None, db: AsyncSession=Depends(get_db) -> User)`
- `get_org_context(org_id: uuid.UUID, user: User=Depends(get_current_user), request: Request=None, db: AsyncSession=Depends(get_db) -> OrgContext)`
- `require_roles(*allowed: str)`
- `require_sensitive_reauth()`
- `resolve_org_id_from_request(org_id: uuid.UUID | None, request: Request | None -> uuid.UUID)`
- `resolve_workforce_org_id_from_request(org_id: uuid.UUID | None, request: Request | None, db: AsyncSession -> uuid.UUID)`

#### [backend/app/api/period_month.py](backend/app/api/period_month.py)

- `parse_period_month_query(raw: str | None -> date | None)`

#### [backend/app/api/v1/__init__.py](backend/app/api/v1/__init__.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/api/v1/admin.py](backend/app/api/v1/admin.py)

- `_notify(db: AsyncSession, **kwargs -> None)`
- `recompute_all(request: Request, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `list_outbox(org_id: uuid.UUID=Query(...), status: str | None=None, event_type: str | None=None, page: int=1, page_size: int=20, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `retry_outbox_event(event_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `system_status(org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `runtime_metrics(org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `runtime_slos(org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `pause_schedule(name: str, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `resume_schedule(name: str, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `run_schedule_now(name: str, request: Request, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `export_audit_logs(org_id: uuid.UUID=Query(...), since: datetime | None=Query(default=None), until: datetime | None=Query(default=None), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `rotate_org_pii(org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `list_deletion_requests(org_id: uuid.UUID=Query(...), limit: int=Query(default=50, ge=1, le=200), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `list_dead_letter(org_id: uuid.UUID=Query(...), status: str | None=None, source_type: str | None=None, page: int=Query(default=1, ge=1), page_size: int=Query(default=20, ge=1, le=100), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `replay_dead_letter(dead_letter_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `dismiss_dead_letter(dead_letter_id: uuid.UUID, org_id: uuid.UUID=Query(...), reason: str | None=Query(default=None), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/ai.py](backend/app/api/v1/ai.py)

- `ai_health(org_id: uuid.UUID=Query(...), live_check: bool=Query(default=False), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db))`
- `ai_summary(body: AISummaryRequest, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_ai_chat_session(body: AIChatSessionCreateIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_ai_chat_sessions(org_id: uuid.UUID=Query(...), mine_only: bool=Query(default=False), limit: int=Query(default=50, ge=1, le=100), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `get_ai_chat_session(session_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `ai_chat(body: AIChatRequest, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/alerts.py](backend/app/api/v1/alerts.py)

- `_coerce_uuid(value: Any, field_name: str -> uuid.UUID | None)`
- `list_alerts(org_id: uuid.UUID=Query(...), status: str | None=Query(default=None), assignee_user_id: uuid.UUID | None=Query(default=None), location_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `dismiss_alert(alert_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db))`
- `assign_alert(alert_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), assignee_user_id: uuid.UUID | None=Query(default=None), body: dict[str, Any] | None=Body(default=None), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db))`
- `acknowledge_alert(alert_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), body: dict[str, Any] | None=Body(default=None), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db))`
- `alert_history(alert_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/analytics.py](backend/app/api/v1/analytics.py)

- `summary(org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), from_date: date=Query(..., alias='from'), to_date: date=Query(..., alias='to'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `cashflow(org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), from_date: date=Query(..., alias='from'), to_date: date=Query(..., alias='to'), granularity: str='month', user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `budget_variance(org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), period: str | None=Query(default=None, description='Month as YYYY-MM or YYYY-MM-DD (normalized to month start). Defaults to current month.'), budget_type: str | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `location_benchmark(org_id: uuid.UUID=Query(...), from_date: date=Query(..., alias='from'), to_date: date=Query(..., alias='to'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `recompute(request: Request, org_id: uuid.UUID=Query(...), idempotency_key: str | None=Header(default=None, alias='Idempotency-Key'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/auth.py](backend/app/api/v1/auth.py)

- `_set_auth_cookies(response: Response, access_token: str, refresh_token: str -> None)`
- `_clear_auth_cookies(response: Response -> None)`
- `_token_response(tok: TokenOut -> TokenOut)`
- `_extract_confirmation_token(body: str | None -> str | None)`
- `_get_refresh_token_from_request(*, request: Request, body_token: str | None=None -> str | None)`
- `register(request: Request, response: Response, body: RegisterIn, db: AsyncSession=Depends(get_db))`
- `login(request: Request, response: Response, body: LoginIn, db: AsyncSession=Depends(get_db))`
- `refresh(request: Request, response: Response, body: TokenRefreshIn, db: AsyncSession=Depends(get_db))`
- `accept_invite(request: Request, body: InviteAcceptIn, db: AsyncSession=Depends(get_db))`
- `confirm(request: Request, body: ConfirmIn, db: AsyncSession=Depends(get_db))`
- `resend_confirmation(request: Request, body: ResendConfirmationIn, db: AsyncSession=Depends(get_db))`
- `dev_confirmation_token(email: str=Query(...), db: AsyncSession=Depends(get_db))`
- `logout(request: Request, response: Response, body: LogoutIn | None=None, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `me(user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `mfa_status(user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `mfa_setup(request: Request, body: MfaSetupIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `mfa_enable(request: Request, body: MfaEnableIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `mfa_disable(request: Request, body: MfaDisableIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `mfa_regenerate_recovery_codes(request: Request, body: MfaRecoveryCodesRegenerateIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_sessions(request: Request, refresh_token: str | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `revoke_session(session_id: uuid.UUID, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `revoke_other_sessions(request: Request, body: RevokeOthersIn=Body(default_factory=RevokeOthersIn), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `reauth(request: Request, body: ReauthIn, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `request_account_deletion(body: AccountDeletionRequestIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_account_deletion_requests(limit: int=Query(default=20, ge=1, le=100), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/budgets.py](backend/app/api/v1/budgets.py)

- `_assert_mutation_role(role: str -> None)`
- `_apply_alert_recalc_headers(response: Response, *, task_id: str, status: str, enqueued: bool -> None)`
- `_notify_alert_recalc(*, db: AsyncSession, org_id: uuid.UUID, source: str, task_id: str, status: str, enqueued: bool -> None)`
- `list_budgets(org_id: uuid.UUID=Query(...), period: str | None=Query(default=None, description='Month as YYYY-MM or first day YYYY-MM-DD (normalized to month start).'), budget_type: str | None=Query(default=None), include_history: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_budget(request: Request, response: Response, body: BudgetCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_budget(request: Request, response: Response, budget_id: uuid.UUID, body: BudgetUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/events.py](backend/app/api/v1/events.py)

- `stream_updates(org_id: uuid.UUID=Query(...), interval_seconds: int=Query(default=10, ge=3, le=60), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/forecast.py](backend/app/api/v1/forecast.py)

- `get_forecast(org_id: uuid.UUID=Query(...), months: int=3, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `override_forecast(body: ForecastOverrideIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/health.py](backend/app/api/v1/health.py)

- `health(db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/integrations.py](backend/app/api/v1/integrations.py)

- `_assert_mutation_role(role: str -> None)`
- `_to_connection_out(connection, accounts -> BankConnectionOut)`
- `_to_payment_connection_out(connection -> PaymentConnectionOut)`
- `create_plaid_link_token(body: PlaidLinkTokenIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `exchange_plaid_public_token(body: PlaidExchangeIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_bank_connections(org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `revoke_bank_connection(connection_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `enqueue_bank_sync(request: Request, connection_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `plaid_webhook(request: Request, plaid_signature: str | None=Header(default=None, alias='X-Plaid-Signature'), db: AsyncSession=Depends(get_db))`
- `connect_stripe(body: StripeConnectIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_payment_connections(org_id: uuid.UUID=Query(...), provider: str=Query(default='STRIPE'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `stripe_webhook(request: Request, stripe_signature: str | None=Header(default=None, alias='Stripe-Signature'), db: AsyncSession=Depends(get_db))`
- `get_payment_reconciliation(org_id: uuid.UUID=Query(...), provider: str=Query(default='STRIPE'), date_from: date | None=Query(default=None), date_to: date | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/inventory.py](backend/app/api/v1/inventory.py)

- `_assert_mutation_role(role: str -> None)`
- `_apply_alert_recalc_headers(response: Response, *, task_id: str, status: str, enqueued: bool -> None)`
- `_notify_alert_recalc(*, db: AsyncSession, org_id: uuid.UUID, source: str, task_id: str, status: str, enqueued: bool -> None)`
- `list_items(org_id: uuid.UUID=Query(...), include_inactive: bool=Query(default=False), location_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_item(request: Request, response: Response, body: InventoryItemCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_stock_event(request: Request, response: Response, body: InventoryStockEventCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_purchase_order(request: Request, response: Response, body: InventoryPurchaseOrderCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `get_forecast(org_id: uuid.UUID=Query(...), lookback_days: int=Query(default=30), horizon_days: int=Query(default=30), location_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/jobs.py](backend/app/api/v1/jobs.py)

- `list_jobs(org_id: uuid.UUID=Query(...), status: str | None=None, task_name: str | None=None, since: datetime | None=None, until: datetime | None=None, page: int=1, page_size: int=20, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `cancel_job(job_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `retry_job(job_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/locations.py](backend/app/api/v1/locations.py)

- `_assert_mutation_role(role: str -> None)`
- `list_locations(org_id: uuid.UUID=Query(...), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_location(body: LocationCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_location(location_id: uuid.UUID, body: LocationUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `delete_location(location_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/notifications.py](backend/app/api/v1/notifications.py)

- `list_notifications(org_id: uuid.UUID=Query(...), unread_only: bool=False, page: int=1, page_size: int=20, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `mark_read(notification_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `mark_all_read(org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/organizations.py](backend/app/api/v1/organizations.py)

- `_billing_out(billing -> OrgBillingOut)`
- `create_org(body: OrganizationCreateIn, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_orgs(user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `invite(org_id: uuid.UUID, body: InviteIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db))`
- `members(org_id: uuid.UUID, _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `get_settings(org_id: uuid.UUID, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_settings(org_id: uuid.UUID, body: OrgSettingsUpdateIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), ctx=Depends(get_org_context), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db))`
- `get_plan_usage(org_id: uuid.UUID, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `get_billing(org_id: uuid.UUID, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), db: AsyncSession=Depends(get_db))`
- `update_billing(org_id: uuid.UUID, body: OrgBillingUpdateIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db))`
- `create_billing_checkout(org_id: uuid.UUID, body: BillingCheckoutIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db))`
- `create_billing_portal(org_id: uuid.UUID, body: BillingPortalIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db))`
- `billing_webhook(request: Request, db: AsyncSession=Depends(get_db))`
- `request_org_deletion(org_id: uuid.UUID, body: OrgDeletionRequestIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER')), __: object=Depends(require_sensitive_reauth()), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/reports.py](backend/app/api/v1/reports.py)

- `list_reports(org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `generate(request: Request, org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), week_start: date=Query(...), idempotency_key: str | None=Header(default=None, alias='Idempotency-Key'), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db))`
- `download(report_id: uuid.UUID, org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/router.py](backend/app/api/v1/router.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/api/v1/runway.py](backend/app/api/v1/runway.py)

- `runway(org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), lookback_months: int=6, conservative: bool=False, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/transactions.py](backend/app/api/v1/transactions.py)

- `_assert_mutation_role(role: str -> None)`
- `_apply_alert_recalc_headers(response: Response, *, task_id: str, status: str, enqueued: bool -> None)`
- `_notify_alert_recalc(*, db: AsyncSession, org_id: uuid.UUID, source: str, task_id: str, status: str, enqueued: bool -> None)`
- `create_tx(request: Request, response: Response, body: TransactionCreateIn, idempotency_key: str | None=Header(default=None, alias='Idempotency-Key'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_tx(org_id: uuid.UUID=Query(...), location_id: uuid.UUID | None=Query(default=None), from_date: str | None=Query(None, alias='from'), to_date: str | None=Query(None, alias='to'), type: str | None=None, category: str | None=None, q: str | None=None, page: int=1, page_size: int=20, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_tx(request: Request, response: Response, tx_id: uuid.UUID, body: TransactionUpdateIn, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db))`
- `delete_tx(request: Request, response: Response, tx_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db))`
- `import_csv(request: Request, response: Response, org_id: uuid.UUID=Form(...), mapping: str | None=Form(None), profile_id: uuid.UUID | None=Form(None), commit: bool=Form(True), file: UploadFile=File(...), idempotency_key: str | None=Header(default=None, alias='Idempotency-Key'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_imports(org_id: uuid.UUID=Query(...), page: int=1, page_size: int=20, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `download_import_errors(import_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `bulk_remap_category(request: Request, response: Response, body: BulkCategoryRemapIn, user: User=Depends(get_current_user), _: object=Depends(require_roles('OWNER', 'EDITOR')), db: AsyncSession=Depends(get_db))`
- `list_import_profiles(org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_import_profile(body: ImportMappingProfileIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_import_profile(profile_id: uuid.UUID, body: ImportMappingProfileUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `delete_import_profile(profile_id: uuid.UUID, org_id: uuid.UUID=Query(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/workforce/__init__.py](backend/app/api/v1/workforce/__init__.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/api/v1/workforce/announcements.py](backend/app/api/v1/workforce/announcements.py)

- `_assert_mutation_role(role: str -> None)`
- `_to_out(row, receipt=None -> WorkforceAnnouncementOut)`
- `_safe_upload_filename(name: str | None -> str)`
- `_presigned_attachment_url(*, object_key: str, filename: str -> str)`
- `_enrich_deliveries(db: AsyncSession, rows: list -> list[WorkforceAnnouncementDeliveryOut])`
- `list_automation_keys(request: Request, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `upload_announcement_attachment(request: Request, org_id: uuid.UUID | None=Query(default=None), file: UploadFile=File(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_announcement_templates(request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_announcement_template(request: Request, body: WorkforceAnnouncementTemplateCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_announcement_template(template_id: uuid.UUID, request: Request, body: WorkforceAnnouncementTemplateUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_announcements(request: Request, org_id: uuid.UUID | None=Query(default=None), include_archived: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_announcement(request: Request, body: WorkforceAnnouncementCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_announcement_deliveries(announcement_id: uuid.UUID, request: Request, org_id: uuid.UUID | None=Query(default=None), status: str | None=Query(default=None, description='Filter: PENDING, RETRYING, SENT, FAILED, or ALL'), page: int=Query(default=1, ge=1, le=10000), page_size: int=Query(default=50, ge=1, le=200), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_announcement(request: Request, announcement_id: uuid.UUID, body: WorkforceAnnouncementUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `publish_announcement(request: Request, announcement_id: uuid.UUID, body: WorkforceAnnouncementPublishIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `archive_announcement(request: Request, announcement_id: uuid.UUID, body: WorkforceAnnouncementArchiveIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `get_announcement(announcement_id: uuid.UUID, request: Request, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `acknowledge_announcement(request: Request, announcement_id: uuid.UUID, body: WorkforceAnnouncementAcknowledgeIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/workforce/attendance.py](backend/app/api/v1/workforce/attendance.py)

- `_assert_mutation_role(role: str -> None)`
- `daily(request: Request, org_id: uuid.UUID | None=Query(default=None), date_value: date=Query(..., alias='date'), employee_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `calendar(request: Request, org_id: uuid.UUID | None=Query(default=None), month: str=Query(..., description='Month in YYYY-MM'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `clock_in(request: Request, body: WorkforceAttendanceClockInIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `clock_out(request: Request, body: WorkforceAttendanceClockOutIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `manual(request: Request, body: WorkforceAttendanceManualIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/workforce/corrections.py](backend/app/api/v1/workforce/corrections.py)

- `_assert_mutation_role(role: str -> None)`
- `list_corrections(request: Request, org_id: uuid.UUID | None=Query(default=None), status: str | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), limit: int=Query(default=200, ge=1, le=500), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `request_correction(request: Request, body: WorkforceAttendanceCorrectionRequestIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `review_correction(request: Request, correction_id: uuid.UUID, body: WorkforceAttendanceCorrectionReviewIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/workforce/departments.py](backend/app/api/v1/workforce/departments.py)

- `_assert_mutation_role(role: str -> None)`
- `list_departments(request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_department(request: Request, body: WorkforceDepartmentCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_department(request: Request, department_id: uuid.UUID, body: WorkforceDepartmentUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `delete_department(request: Request, department_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/workforce/employees.py](backend/app/api/v1/workforce/employees.py)

- `_assert_mutation_role(role: str -> None)`
- `_assert_owner(role: str -> None)`
- `_redact_employee_for_role(row: WorkforceEmployeeOut, role: str -> WorkforceEmployeeOut)`
- `list_employees(request: Request, org_id: uuid.UUID | None=Query(default=None), q: str | None=Query(default=None), department_id: uuid.UUID | None=Query(default=None), title_id: uuid.UUID | None=Query(default=None), manager_employee_id: uuid.UUID | None=Query(default=None), employment_status: str | None=Query(default=None), include_inactive: bool=Query(default=False), limit: int=Query(default=200, ge=1, le=5000), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `get_employee(request: Request, employee_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_employee(request: Request, body: WorkforceEmployeeCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_employee(request: Request, employee_id: uuid.UUID, body: WorkforceEmployeeUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `delete_employee(request: Request, employee_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/workforce/hr_admin.py](backend/app/api/v1/workforce/hr_admin.py)

- `_assert_mutation_role(role: str -> None)`
- `_safe_upload_filename(name: str | None -> str)`
- `_presigned_url(*, object_key: str -> str)`
- `_svc(db: AsyncSession -> WorkforceHrService)`
- `_notify_workforce_event(db: AsyncSession, *, org_id: uuid.UUID, title: str, message: str, link: str, metadata_json: dict | None=None -> None)`
- `list_policies(request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), limit: int=Query(default=200, ge=1, le=500), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_policy(request: Request, body: WorkforcePolicyCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `publish_policy(policy_id: uuid.UUID, request: Request, body: WorkforcePolicyPublishIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_policy_acks(policy_id: uuid.UUID, request: Request, org_id: uuid.UUID | None=Query(default=None), limit: int=Query(default=5000, ge=1, le=10000), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `acknowledge_policy(policy_id: uuid.UUID, request: Request, body: WorkforcePolicyAckCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `upload_document(request: Request, org_id: uuid.UUID | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), policy_id: uuid.UUID | None=Query(default=None), file: UploadFile=File(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_documents(request: Request, org_id: uuid.UUID | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), policy_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), limit: int=Query(default=500, ge=1, le=2000), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `deactivate_document(document_id: uuid.UUID, request: Request, body: WorkforceDocumentDeactivateIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_checklist(request: Request, org_id: uuid.UUID | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), kind: str | None=Query(default=None), include_done: bool=Query(default=True), limit: int=Query(default=5000, ge=1, le=10000), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_checklist_item(request: Request, body: WorkforceChecklistItemCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `set_checklist_done(item_id: uuid.UUID, request: Request, body: WorkforceChecklistDoneIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/workforce/intelligence.py](backend/app/api/v1/workforce/intelligence.py)

- `workforce_dashboard_intel(request: Request, org_id: uuid.UUID | None=Query(default=None), as_of: date | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `workforce_reports_summary(request: Request, org_id: uuid.UUID | None=Query(default=None), from_date: date=Query(..., alias='from'), to_date: date=Query(..., alias='to'), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/workforce/leave.py](backend/app/api/v1/workforce/leave.py)

- `_assert_mutation_role(role: str -> None)`
- `_assert_owner(role: str -> None)`
- `_svc(db: AsyncSession -> WorkforceLeaveService)`
- `_notify_workforce_event(db: AsyncSession, *, org_id: uuid.UUID, title: str, message: str, metadata_json: dict | None=None -> None)`
- `list_leave_types(request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_leave_type(request: Request, body: WorkforceLeaveTypeCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_leave_type(request: Request, leave_type_id: uuid.UUID, body: WorkforceLeaveTypeUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `delete_leave_type(request: Request, leave_type_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_balances(request: Request, org_id: uuid.UUID | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), year: int | None=Query(default=None), limit: int=Query(default=2000, ge=1, le=5000), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `allocate_balance(request: Request, body: WorkforceLeaveBalanceAllocateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_requests(request: Request, org_id: uuid.UUID | None=Query(default=None), status: str | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), from_date: date | None=Query(default=None), to_date: date | None=Query(default=None), limit: int=Query(default=200, ge=1, le=500), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_request(request: Request, body: WorkforceLeaveRequestCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `decide_request(request: Request, request_id: uuid.UUID, body: WorkforceLeaveRequestDecisionIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/workforce/payroll.py](backend/app/api/v1/workforce/payroll.py)

- `_assert_mutation_role(role: str -> None)`
- `_assert_owner_role(role: str -> None)`
- `_redact_entry_out(entry: WorkforcePayrollEntryOut, role: str -> WorkforcePayrollEntryOut)`
- `_redact_adjustment_out(row: WorkforcePayrollAdjustmentOut, role: str -> WorkforcePayrollAdjustmentOut)`
- `_entry_out_from_model(row, role: str -> WorkforcePayrollEntryOut)`
- `_svc(db: AsyncSession -> WorkforcePayrollService)`
- `_notify_workforce_event(db: AsyncSession, *, org_id: uuid.UUID, title: str, message: str, metadata_json: dict | None=None -> None)`
- `list_periods(request: Request, org_id: uuid.UUID | None=Query(default=None), limit: int=Query(default=50, ge=1, le=200), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_period(request: Request, body: WorkforcePayrollPeriodCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `generate(request: Request, payroll_period_id: uuid.UUID, body: WorkforcePayrollGenerateDraftIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_entries(request: Request, payroll_period_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `approve(request: Request, payroll_period_id: uuid.UUID, body: WorkforcePayrollPeriodActionIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `mark_paid(request: Request, payroll_period_id: uuid.UUID, body: WorkforcePayrollPeriodActionIn=Body(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `export_csv(request: Request, payroll_period_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_adjustment(request: Request, body: WorkforcePayrollAdjustmentCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `delete_adjustment(request: Request, adjustment_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), payroll_period_id: uuid.UUID=Query(...), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `payslip_preview(request: Request, entry_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `payslip_pdf(request: Request, entry_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/workforce/router.py](backend/app/api/v1/workforce/router.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/api/v1/workforce/shifts.py](backend/app/api/v1/workforce/shifts.py)

- `_assert_mutation_role(role: str -> None)`
- `list_shifts(request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_shift(request: Request, body: WorkforceShiftCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_shift(request: Request, shift_id: uuid.UUID, body: WorkforceShiftUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `delete_shift(request: Request, shift_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `list_assignments(request: Request, org_id: uuid.UUID | None=Query(default=None), employee_id: uuid.UUID | None=Query(default=None), shift_id: uuid.UUID | None=Query(default=None), as_of: date | None=Query(default=None), limit: int=Query(default=200, ge=1, le=500), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_assignment(request: Request, body: WorkforceShiftAssignmentCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/api/v1/workforce/titles.py](backend/app/api/v1/workforce/titles.py)

- `_assert_mutation_role(role: str -> None)`
- `list_titles(request: Request, org_id: uuid.UUID | None=Query(default=None), include_inactive: bool=Query(default=False), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `create_title(request: Request, body: WorkforceTitleCreateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `update_title(request: Request, title_id: uuid.UUID, body: WorkforceTitleUpdateIn=Body(...), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`
- `delete_title(request: Request, title_id: uuid.UUID, org_id: uuid.UUID | None=Query(default=None), _reauth: None=Depends(require_sensitive_reauth()), user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db))`

#### [backend/app/core/auth_lockout.py](backend/app/core/auth_lockout.py)

- `_normalize_email(email: str -> str)`
- `_normalize_ip(ip: str | None -> str)`
- `_email_fail_key(email: str -> str)`
- `_ip_fail_key(ip: str | None -> str)`
- `_scope_lock_key(email: str, ip: str | None -> str)`
- `_scope_escalation_key(email: str, ip: str | None -> str)`
- Class `LockoutResult`
- `lockout_metrics( -> dict[str, int])`
- `is_locked(email: str, ip: str | None -> LockoutResult)`
- `clear_login_failures(email: str, ip: str | None -> None)`
- `record_login_failure(email: str, ip: str | None -> LockoutResult)`

#### [backend/app/core/config.py](backend/app/core/config.py)

- Class `Settings`
  - `_validate_email_provider(self)`
- `get_settings( -> Settings)`

#### [backend/app/core/error_envelope.py](backend/app/core/error_envelope.py)

- `code_for_status(status_code: int -> str)`
- `error_payload(*, request: Request | None, status_code: int, message: str, details: object | None=None, code: str | None=None -> dict[str, object])`
- `detail_to_message(detail: object, default: str -> str)`

#### [backend/app/core/logging.py](backend/app/core/logging.py)

- `configure_logging( -> None)`

#### [backend/app/core/mfa.py](backend/app/core/mfa.py)

- `_fernet_from_secret()`
- `encrypt_mfa_secret(secret: str -> str)`
- `decrypt_mfa_secret(secret_encrypted: str -> str)`
- `generate_totp_secret( -> str)`
- `build_totp_uri(*, email: str, secret: str, issuer: str -> str)`
- `_totp_code(secret: str, counter: int -> str)`
- `verify_totp_code(secret: str, code: str, *, now: datetime | None=None, window: int=1 -> bool)`

#### [backend/app/core/middleware.py](backend/app/core/middleware.py)

- Class `RequestContextMiddleware`
  - `dispatch(self, request: Request, call_next)`
  - `_csrf_validation_failed(self, request: Request, settings: Settings -> bool)`
  - `_https_required_but_missing(request: Request, settings: Settings -> bool)`

#### [backend/app/core/observability.py](backend/app/core/observability.py)

- `init_sentry(settings: Settings, service_name: str -> None)`

#### [backend/app/core/pii_crypto.py](backend/app/core/pii_crypto.py)

- `_load_keyring( -> dict[str, Fernet])`
- `_active_fernet( -> tuple[str, Fernet] | None)`
- `pii_encrypt(value: str | None -> str | None)`
- `pii_decrypt(value: str | None -> str | None)`
- `pii_reencrypt(value: str | None -> str | None)`
- `pii_hash(value: str | None -> str | None)`
- `active_pii_key_id( -> str)`
- `generate_pii_key( -> str)`

#### [backend/app/core/rate_limit.py](backend/app/core/rate_limit.py)

- `enforce_auth_rate_limit(request: Request, action: str, per_minute: int | None=None -> None)`

#### [backend/app/core/security.py](backend/app/core/security.py)

- `hash_password(password: str -> str)`
- `verify_password(password: str, password_hash: str -> bool)`
- `create_token(subject: str, token_type: str, expires_delta: timedelta, extra: dict[str, Any] | None=None -> str)`
- `decode_token(token: str -> dict[str, Any] | None)`
- `access_ttl( -> timedelta)`
- `refresh_ttl( -> timedelta)`

#### [backend/app/core/slo_metrics.py](backend/app/core/slo_metrics.py)

- Class `RequestSample`
- `record_runtime_sample(*, method: str, path: str, status_code: int, latency_ms: float -> None)`
- `runtime_slo_snapshot(*, window_seconds: int=300, p95_threshold_ms: float=2000.0, error_rate_threshold_pct: float=1.0, top_n: int=20 -> dict)`

#### [backend/app/db/base.py](backend/app/db/base.py)

- Class `Base`

#### [backend/app/db/migrations_utils.py](backend/app/db/migrations_utils.py)

- `get_metadata()`

#### [backend/app/db/session.py](backend/app/db/session.py)

- `_pool_setting(default: int, role_override: int | None -> int)`
- `get_db( -> AsyncGenerator[AsyncSession, None])`

#### [backend/app/domain/__init__.py](backend/app/domain/__init__.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/domain/repos/__init__.py](backend/app/domain/repos/__init__.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/domain/repos/ai_chat_repo.py](backend/app/domain/repos/ai_chat_repo.py)

- Class `AIChatRepo`
  - `__init__(self, db: AsyncSession)`
  - `create_session(self, session: AIChatSession -> AIChatSession)`
  - `get_session(self, *, org_id: uuid.UUID, session_id: uuid.UUID -> AIChatSession | None)`
  - `list_sessions(self, *, org_id: uuid.UUID, created_by_user_id: uuid.UUID | None=None, limit: int=50 -> list[AIChatSession])`
  - `touch_session(self, *, session: AIChatSession, at: datetime -> AIChatSession)`
  - `create_message(self, message: AIChatMessage -> AIChatMessage)`
  - `list_messages(self, *, org_id: uuid.UUID, session_id: uuid.UUID, limit: int=100 -> list[AIChatMessage])`

#### [backend/app/domain/repos/alerts_repo.py](backend/app/domain/repos/alerts_repo.py)

- Class `AlertRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_alerts(self, org_id: uuid.UUID, status: str | None, assigned_to_user_id: uuid.UUID | None=None, location_id: uuid.UUID | None=None -> list[Alert])`
  - `get(self, alert_id: uuid.UUID, org_id: uuid.UUID -> Alert | None)`
  - `save(self, alert: Alert -> Alert)`
  - `clear_open(self, org_id: uuid.UUID -> int)`

#### [backend/app/domain/repos/analytics_repo.py](backend/app/domain/repos/analytics_repo.py)

- Class `AnalyticsRepo`
  - `__init__(self, db: AsyncSession)`
  - `month_totals(self, org_id: uuid.UUID, month: date -> tuple[Decimal, Decimal])`
  - `summary_snapshot(self, org_id: uuid.UUID, month: date, *, location_id: uuid.UUID | None=None -> dict[str, Decimal | int])`
  - `summary_snapshot_for_location(self, *, org_id: uuid.UUID, month: date, location_id: uuid.UUID -> dict[str, Decimal | int])`
  - `cash_balance(self, org_id: uuid.UUID, *, location_id: uuid.UUID | None=None -> Decimal)`
  - `monthly_lookback(self, org_id: uuid.UUID, months: int, *, location_id: uuid.UUID | None=None -> list[MonthlyAggregate])`
  - `alerts_open_count(self, org_id: uuid.UUID -> int)`
  - `location_benchmark(self, org_id: uuid.UUID, from_date: date, to_date: date -> dict)`
  - `runway_threshold_days(self, org_id: uuid.UUID -> int)`
  - `transaction_month_starts(self, org_id: uuid.UUID, *, location_id: uuid.UUID | None=None -> list[date])`

#### [backend/app/domain/repos/audit_repo.py](backend/app/domain/repos/audit_repo.py)

- Class `AuditRepo`
  - `__init__(self, db: AsyncSession)`
  - `log(self, actor_user_id: uuid.UUID | None, org_id: uuid.UUID | None, action: str, entity_type: str, entity_id: str, metadata_json: dict -> None)`
  - `list_entity_events(self, *, org_id: uuid.UUID, entity_type: str, entity_id: str, actions: list[str] | None=None, limit: int=100 -> list[AuditLog])`
  - `list_export_events(self, *, org_id: uuid.UUID, since: datetime | None=None, until: datetime | None=None, limit: int=5000 -> list[AuditLog])`

#### [backend/app/domain/repos/auth_repo.py](backend/app/domain/repos/auth_repo.py)

- Class `AuthRepo`
  - `__init__(self, db: AsyncSession)`
  - `get_user_by_email(self, email: str -> User | None)`
  - `get_user(self, user_id: uuid.UUID -> User | None)`
  - `create_user(self, email: str, password_hash: str, is_active: bool=True -> User)`
  - `save_user(self, user: User -> User)`
  - `create_token_session(self, user_id: uuid.UUID, refresh_token_hash: str, expires_at: datetime, user_agent: str | None, ip_address: str | None -> TokenSession)`
  - `get_token_session(self, refresh_token_hash: str -> TokenSession | None)`
  - `get_session_by_id(self, session_id: uuid.UUID, user_id: uuid.UUID -> TokenSession | None)`
  - `list_sessions_for_user(self, user_id: uuid.UUID, *, include_revoked: bool=False -> list[TokenSession])`
  - `revoke_session(self, session: TokenSession -> None)`
  - `revoke_token(self, token: TokenSession -> None)`
  - `touch_session(self, token: TokenSession -> None)`
  - `rotate_token(self, token: TokenSession, replaced_by_token_hash: str -> None)`
  - `revoke_all_user_sessions(self, user_id: uuid.UUID, except_session_id: uuid.UUID | None=None -> int)`
  - `memberships_for_user(self, user_id: uuid.UUID -> list[Membership])`
  - `create_confirmation_token(self, user_id: uuid.UUID, token_hash: str, expires_at: datetime, *, code_hash: str | None=None, code_expires_at: datetime | None=None, code_max_attempts: int=5 -> AccountConfirmationToken)`
  - `get_confirmation_token(self, token_hash: str -> AccountConfirmationToken | None)`
  - `get_pending_confirmation_token_for_user(self, user_id: uuid.UUID -> AccountConfirmationToken | None)`
  - `get_confirmation_token_by_code_hash_for_user(self, *, user_id: uuid.UUID, code_hash: str -> AccountConfirmationToken | None)`
  - `invalidate_unused_confirmation_tokens(self, user_id: uuid.UUID -> int)`
  - `increment_confirmation_code_attempts(self, token: AccountConfirmationToken -> None)`
  - `mark_confirmation_token_used(self, token: AccountConfirmationToken -> None)`

#### [backend/app/domain/repos/bank_repo.py](backend/app/domain/repos/bank_repo.py)

- Class `BankRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_connections(self, org_id: uuid.UUID -> list[BankConnection])`
  - `get_connection(self, connection_id: uuid.UUID, org_id: uuid.UUID -> BankConnection | None)`
  - `get_connection_by_external(self, *, org_id: uuid.UUID, provider: str, external_item_id: str -> BankConnection | None)`
  - `save_connection(self, connection: BankConnection -> BankConnection)`
  - `list_active_connections_by_external_item(self, *, provider: str, external_item_id: str -> list[BankConnection])`
  - `list_active_connections(self -> list[BankConnection])`
  - `replace_accounts(self, *, org_id: uuid.UUID, connection_id: uuid.UUID, accounts: list[BankAccount] -> None)`
  - `get_accounts(self, *, org_id: uuid.UUID, connection_id: uuid.UUID -> list[BankAccount])`
  - `get_cursor(self, *, connection_id: uuid.UUID -> BankSyncCursor | None)`
  - `upsert_cursor(self, *, org_id: uuid.UUID, connection_id: uuid.UUID, cursor_value: str | None -> BankSyncCursor)`
  - `create_sync_run(self, *, org_id: uuid.UUID, connection_id: uuid.UUID, triggered_by_user_id: uuid.UUID | None, cursor_before: str | None -> BankSyncRun)`
  - `save_sync_run(self, run: BankSyncRun -> BankSyncRun)`
  - `existing_external_transaction_ids(self, *, connection_id: uuid.UUID, external_transaction_ids: list[str] -> set[str])`
  - `record_synced_transaction(self, *, org_id: uuid.UUID, connection_id: uuid.UUID, transaction_id: uuid.UUID | None, external_transaction_id: str, posted_date, amount: Decimal | None, currency_code: str | None -> BankSyncedTransaction)`

#### [backend/app/domain/repos/budget_repo.py](backend/app/domain/repos/budget_repo.py)

- Class `BudgetRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_budgets(self, org_id: uuid.UUID, period_month: date | None=None, budget_type: str | None=None, include_history: bool=False -> list[Budget])`
  - `get_budget(self, budget_id: uuid.UUID, org_id: uuid.UUID -> Budget | None)`
  - `max_version(self, *, org_id: uuid.UUID, category: str, period_month: date, budget_type: str -> int)`
  - `clear_current(self, *, org_id: uuid.UUID, category: str, period_month: date, budget_type: str -> int)`
  - `save(self, budget: Budget -> Budget)`
  - `monthly_actuals_by_category(self, *, org_id: uuid.UUID, period_start: date, period_end_exclusive: date, budget_type: str | None=None, location_id: uuid.UUID | None=None -> dict[str, Decimal])`

#### [backend/app/domain/repos/dead_letter_repo.py](backend/app/domain/repos/dead_letter_repo.py)

- Class `DeadLetterRepo`
  - `__init__(self, db: AsyncSession)`
  - `record_failure(self, *, org_id: uuid.UUID | None, source_type: str, source_id: uuid.UUID | None, source_task_id: str | None, source_name: str, attempts: int, last_error: str | None, payload: dict | None, metadata_json: dict | None=None -> DeadLetterEvent)`
  - `by_id(self, dead_letter_id: uuid.UUID -> DeadLetterEvent | None)`
  - `list_events(self, *, org_id: uuid.UUID, status: str | None, source_type: str | None, page: int, page_size: int -> tuple[list[DeadLetterEvent], int])`
  - `counts_by_status(self, *, org_id: uuid.UUID -> dict[str, int])`
  - `open_count(self, *, org_id: uuid.UUID -> int)`
  - `mark_replayed(self, event: DeadLetterEvent, *, metadata_json: dict | None=None -> DeadLetterEvent)`
  - `mark_dismissed(self, event: DeadLetterEvent, *, reason: str | None=None -> DeadLetterEvent)`

#### [backend/app/domain/repos/deletion_repo.py](backend/app/domain/repos/deletion_repo.py)

- Class `DeletionRepo`
  - `__init__(self, db: AsyncSession)`
  - `create_request(self, *, scope: str, requested_by_user_id: uuid.UUID | None, target_user_id: uuid.UUID | None, target_org_id: uuid.UUID | None, reason: str | None, delete_after: datetime -> DeletionRequest)`
  - `latest_pending_for_user(self, user_id: uuid.UUID -> DeletionRequest | None)`
  - `latest_pending_for_org(self, org_id: uuid.UUID -> DeletionRequest | None)`
  - `due_requests(self, now: datetime, limit: int=100 -> list[DeletionRequest])`
  - `mark_processed(self, row: DeletionRequest, *, processed_at: datetime -> None)`
  - `list_for_user(self, user_id: uuid.UUID, *, limit: int=20 -> list[DeletionRequest])`
  - `list_for_org(self, org_id: uuid.UUID, *, limit: int=50 -> list[DeletionRequest])`

#### [backend/app/domain/repos/forecast_repo.py](backend/app/domain/repos/forecast_repo.py)

- Class `ForecastRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_forecasts(self, org_id: uuid.UUID, months: int -> list[Forecast])`
  - `get_one(self, org_id: uuid.UUID, month: date, scenario: str -> Forecast | None)`
  - `save(self, forecast: Forecast -> Forecast)`
  - `delete_for_org(self, org_id: uuid.UUID -> int)`

#### [backend/app/domain/repos/idempotency_repo.py](backend/app/domain/repos/idempotency_repo.py)

- Class `IdempotencyRepo`
  - `__init__(self, db: AsyncSession)`
  - `get_active(self, *, org_id: uuid.UUID, user_id: uuid.UUID, endpoint: str, idempotency_key: str, now: datetime -> IdempotencyKey | None)`
  - `upsert_completed(self, *, org_id: uuid.UUID, user_id: uuid.UUID, endpoint: str, idempotency_key: str, request_hash: str, status_code: int, response_json: dict, expires_at: datetime -> None)`

#### [backend/app/domain/repos/import_profile_repo.py](backend/app/domain/repos/import_profile_repo.py)

- Class `ImportProfileRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_visible(self, org_id: uuid.UUID, user_id: uuid.UUID -> list[ImportMappingProfile])`
  - `get(self, profile_id: uuid.UUID, org_id: uuid.UUID -> ImportMappingProfile | None)`
  - `create(self, profile: ImportMappingProfile -> ImportMappingProfile)`
  - `save(self, profile: ImportMappingProfile -> ImportMappingProfile)`
  - `delete(self, profile: ImportMappingProfile -> None)`

#### [backend/app/domain/repos/import_repo.py](backend/app/domain/repos/import_repo.py)

- Class `ImportRepo`
  - `__init__(self, db: AsyncSession)`
  - `create(self, record: TransactionImport -> TransactionImport)`
  - `list_imports(self, org_id: uuid.UUID, page: int, page_size: int -> tuple[list[TransactionImport], int])`
  - `get(self, import_id: uuid.UUID, org_id: uuid.UUID -> TransactionImport | None)`

#### [backend/app/domain/repos/inventory_repo.py](backend/app/domain/repos/inventory_repo.py)

- `_location_filter(column, location_id: uuid.UUID | None)`
- Class `InventoryRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_items(self, *, org_id: uuid.UUID, include_inactive: bool=False, location_id: uuid.UUID | None=None -> list[InventoryItem])`
  - `get_item(self, *, org_id: uuid.UUID, item_id: uuid.UUID -> InventoryItem | None)`
  - `get_item_by_sku(self, *, org_id: uuid.UUID, sku: str, location_id: uuid.UUID | None -> InventoryItem | None)`
  - `create_item(self, item: InventoryItem -> InventoryItem)`
  - `get_stock_level(self, *, org_id: uuid.UUID, item_id: uuid.UUID, location_id: uuid.UUID | None, for_update: bool=False -> InventoryStockLevel | None)`
  - `upsert_stock_level(self, *, org_id: uuid.UUID, item_id: uuid.UUID, location_id: uuid.UUID | None, delta_qty: Decimal -> InventoryStockLevel)`
  - `create_stock_event(self, event: InventoryStockEvent -> InventoryStockEvent)`
  - `outbound_quantity(self, *, org_id: uuid.UUID, item_id: uuid.UUID, location_id: uuid.UUID | None, from_dt: datetime, to_dt: datetime -> Decimal)`
  - `create_purchase_order(self, row: InventoryPurchaseOrder -> InventoryPurchaseOrder)`
  - `open_purchase_quantity(self, *, org_id: uuid.UUID, item_id: uuid.UUID, location_id: uuid.UUID | None, horizon_date: date -> Decimal)`
  - `upsert_sales_velocity(self, *, org_id: uuid.UUID, item_id: uuid.UUID, location_id: uuid.UUID | None, window_days: int, units_per_day: Decimal, basis_start: date, basis_end: date -> InventorySalesVelocity)`

#### [backend/app/domain/repos/job_repo.py](backend/app/domain/repos/job_repo.py)

- Class `JobRepo`
  - `__init__(self, db: AsyncSession)`
  - `by_dedupe_key(self, dedupe_key: str, org_id: uuid.UUID | None=None -> JobState | None)`
  - `upsert_pending(self, *, task_id: str, task_name: str, dedupe_key: str, payload: dict, org_id: uuid.UUID | None, request_id: str | None, correlation_id: str | None -> JobState)`
  - `upsert_running(self, *, task_id: str, task_name: str, dedupe_key: str, payload: dict, org_id: uuid.UUID | None, request_id: str | None, correlation_id: str | None -> JobState)`
  - `mark_retrying(self, task_id: str, *, retry_count: int, error: str, traceback_summary: str | None -> None)`
  - `mark_failed(self, task_id: str, *, retry_count: int, error: str, traceback_summary: str | None -> None)`
  - `mark_succeeded(self, task_id: str, result: dict | None=None -> None)`
  - `mark_cancelled(self, task_id: str, *, error: str | None=None -> None)`
  - `list_jobs(self, *, org_id: uuid.UUID, status: str | None, task_name: str | None, since: datetime | None, until: datetime | None, page: int, page_size: int -> tuple[list[JobState], int])`
  - `list_system_jobs(self, *, task_name: str | None=None, page: int=1, page_size: int=20 -> tuple[list[JobState], int])`
  - `by_id(self, job_id: uuid.UUID -> JobState | None)`
  - `by_task_id(self, task_id: str -> JobState | None)`
  - `count_active(self, org_id: uuid.UUID -> int)`
  - `oldest_active_created_at(self, org_id: uuid.UUID -> datetime | None)`

#### [backend/app/domain/repos/location_repo.py](backend/app/domain/repos/location_repo.py)

- Class `LocationRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_by_org(self, org_id: uuid.UUID, *, include_inactive: bool=False -> list[Location])`
  - `get_by_id(self, location_id: uuid.UUID, org_id: uuid.UUID -> Location | None)`
  - `get_by_name_or_code(self, *, org_id: uuid.UUID, name: str, code: str | None, exclude_location_id: uuid.UUID | None=None -> Location | None)`
  - `create(self, location: Location -> Location)`

#### [backend/app/domain/repos/notification_repo.py](backend/app/domain/repos/notification_repo.py)

- Class `NotificationRepo`
  - `__init__(self, db: AsyncSession)`
  - `create(self, *, title: str, message: str | None, category: str='INFO', org_id: uuid.UUID | None=None, user_id: uuid.UUID | None=None, link: str | None=None, metadata_json: dict | None=None -> Notification)`
  - `list_for_user(self, *, user_id: uuid.UUID, org_id: uuid.UUID | None, unread_only: bool, page: int, page_size: int -> tuple[list[Notification], int])`
  - `mark_read(self, notification_id: uuid.UUID, *, user_id: uuid.UUID -> Notification | None)`
  - `mark_all_read(self, *, user_id: uuid.UUID, org_id: uuid.UUID | None -> int)`

#### [backend/app/domain/repos/org_repo.py](backend/app/domain/repos/org_repo.py)

- Class `OrgRepo`
  - `__init__(self, db: AsyncSession)`
  - `create_org(self, name: str -> Organization)`
  - `add_membership(self, user_id: uuid.UUID, org_id: uuid.UUID, role: str -> Membership)`
  - `list_orgs_for_user(self, user_id: uuid.UUID -> list[tuple[Organization, Membership]])`
  - `membership(self, user_id: uuid.UUID, org_id: uuid.UUID -> Membership | None)`
  - `owner_org_ids_requiring_mfa(self, user_id: uuid.UUID -> list[uuid.UUID])`
  - `members(self, org_id: uuid.UUID -> list[tuple[Membership, User]])`
  - `get_settings(self, org_id: uuid.UUID -> OrganizationSetting | None)`
  - `save_settings(self, settings: OrganizationSetting -> OrganizationSetting)`
  - `get_billing(self, org_id: uuid.UUID -> OrganizationBilling | None)`
  - `get_billing_by_customer_id(self, customer_id: str -> OrganizationBilling | None)`
  - `save_billing(self, billing: OrganizationBilling -> OrganizationBilling)`
  - `get_org(self, org_id: uuid.UUID -> Organization | None)`
  - `create_invite(self, org_id: uuid.UUID, email: str, role: str, invited_by: uuid.UUID, token_hash: str, expires_at: datetime -> OrganizationInvite)`
  - `get_invite_by_hash(self, token_hash: str -> OrganizationInvite | None)`

#### [backend/app/domain/repos/outbox_repo.py](backend/app/domain/repos/outbox_repo.py)

- Class `OutboxRepo`
  - `__init__(self, db: AsyncSession)`
  - `create_event(self, *, event_type: str, payload: dict, org_id: uuid.UUID | None=None, correlation_id: str | None=None, dedupe_key: str | None=None, max_attempts: int=5 -> OutboxEvent)`
  - `claim_pending(self, *, limit: int=100 -> list[OutboxEvent])`
  - `mark_sent(self, event: OutboxEvent -> None)`
  - `mark_sent_dry_run(self, event: OutboxEvent -> None)`
  - `mark_retry_or_failed(self, event: OutboxEvent, error: str -> None)`
  - `requeue(self, event: OutboxEvent, *, reset_attempts: bool=False -> OutboxEvent)`
  - `by_id(self, event_id: uuid.UUID -> OutboxEvent | None)`
  - `list_events(self, *, org_id: uuid.UUID | None, status: str | None, event_type: str | None, page: int, page_size: int -> tuple[list[OutboxEvent], int])`
  - `counts_by_status(self, *, org_id: uuid.UUID | None -> dict[str, int])`

#### [backend/app/domain/repos/payment_repo.py](backend/app/domain/repos/payment_repo.py)

- Class `PaymentRepo`
  - `__init__(self, db: AsyncSession)`
  - `get_connection_by_org_provider(self, *, org_id: uuid.UUID, provider: str='STRIPE' -> PaymentProcessorConnection | None)`
  - `list_connections(self, *, org_id: uuid.UUID, provider: str | None=None -> list[PaymentProcessorConnection])`
  - `get_connection_by_provider_account(self, *, provider: str, provider_account_id: str -> PaymentProcessorConnection | None)`
  - `upsert_connection(self, *, org_id: uuid.UUID, connected_by_user_id: uuid.UUID | None, provider: str, provider_account_id: str | None, metadata_json: dict | None=None, status: str='ACTIVE' -> PaymentProcessorConnection)`
  - `get_webhook_event(self, *, provider: str, provider_event_id: str -> PaymentWebhookEvent | None)`
  - `create_webhook_event(self, *, org_id: uuid.UUID | None, connection_id: uuid.UUID | None, provider: str, provider_event_id: str, event_type: str, payload: dict -> PaymentWebhookEvent)`
  - `mark_webhook_event_status(self, row: PaymentWebhookEvent, *, status: str, error_message: str | None=None -> PaymentWebhookEvent)`
  - `upsert_ledger_entry(self, *, org_id: uuid.UUID, connection_id: uuid.UUID | None, webhook_event_id: uuid.UUID | None, provider: str, external_event_id: str, entry_type: str, direction: str, amount: Decimal, currency_code: str, occurred_at: datetime, description: str | None, metadata_json: dict | None=None -> PaymentLedgerEntry)`
  - `processor_totals(self, *, org_id: uuid.UUID, provider: str, date_from: date, date_to: date -> dict[str, Decimal | int])`
  - `transaction_totals(self, *, org_id: uuid.UUID, date_from: date, date_to: date -> dict[str, Decimal | int])`

#### [backend/app/domain/repos/plan_repo.py](backend/app/domain/repos/plan_repo.py)

- Class `PlanRepo`
  - `__init__(self, db: AsyncSession)`
  - `get_plan(self, org_id: uuid.UUID -> OrganizationPlan | None)`
  - `save_plan(self, plan: OrganizationPlan -> OrganizationPlan)`
  - `get_usage(self, org_id: uuid.UUID, metric: str, period_start: date -> UsageMeter | None)`
  - `ensure_usage(self, org_id: uuid.UUID, metric: str, period_start: date, soft_limit: int -> UsageMeter)`
  - `increment_usage(self, usage: UsageMeter, delta: int -> UsageMeter)`

#### [backend/app/domain/repos/report_repo.py](backend/app/domain/repos/report_repo.py)

- Class `ReportRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_reports(self, org_id: uuid.UUID, *, location_id: uuid.UUID | None=None -> list[Report])`
  - `get(self, report_id: uuid.UUID, org_id: uuid.UUID, *, location_id: uuid.UUID | None=None -> Report | None)`
  - `get_by_week(self, org_id: uuid.UUID, week_start: date, *, location_id: uuid.UUID | None=None -> Report | None)`
  - `save(self, report: Report -> Report)`

#### [backend/app/domain/repos/schedule_repo.py](backend/app/domain/repos/schedule_repo.py)

- Class `ScheduleRepo`
  - `__init__(self, db: AsyncSession)`
  - `get(self, name: str -> ScheduleControl | None)`
  - `list_all(self -> list[ScheduleControl])`
  - `set_paused(self, name: str, paused: bool -> ScheduleControl)`

#### [backend/app/domain/repos/transaction_repo.py](backend/app/domain/repos/transaction_repo.py)

- Class `TransactionRepo`
  - `__init__(self, db: AsyncSession)`
  - `create(self, tx: Transaction -> Transaction)`
  - `get_by_id_org(self, tx_id: uuid.UUID, org_id: uuid.UUID -> Transaction | None)`
  - `delete(self, tx: Transaction -> None)`
  - `list(self, org_id: uuid.UUID, location_id: uuid.UUID | None, date_from: date | None, date_to: date | None, tx_type: str | None, category: str | None, q: str | None, page: int, page_size: int -> tuple[list[Transaction], int])`
  - `duplicate_count(self, org_id: uuid.UUID, txs: list[dict] -> int)`
  - `existing_duplicate_keys(self, org_id: uuid.UUID, txs: list[dict] -> set[tuple])`
  - `upsert_monthly_aggregate(self, org_id: uuid.UUID, d: date -> None)`
  - `bulk_remap_category(self, org_id: uuid.UUID, from_category: str, to_category: str, from_date: date | None=None, to_date: date | None=None -> int)`
  - `list_month_starts_for_category(self, org_id: uuid.UUID, category: str, from_date: date | None=None, to_date: date | None=None -> list[date])`

#### [backend/app/domain/repos/workforce_announcement_delivery_repo.py](backend/app/domain/repos/workforce_announcement_delivery_repo.py)

- Class `WorkforceAnnouncementDeliveryRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_for_announcement(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID, limit: int=500 -> list[WorkforceAnnouncementDelivery])`
  - `list_for_announcement_page(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID, status: str | None, page: int, page_size: int -> tuple[list[WorkforceAnnouncementDelivery], int])`
  - `create(self, row: WorkforceAnnouncementDelivery -> WorkforceAnnouncementDelivery)`
  - `get_by_id(self, *, delivery_id: uuid.UUID -> WorkforceAnnouncementDelivery | None)`
  - `mark_sent(self, *, delivery_id: uuid.UUID, outbox_event_id: uuid.UUID | None=None -> None)`
  - `mark_sent_dry_run(self, *, delivery_id: uuid.UUID, outbox_event_id: uuid.UUID | None=None -> None)`
  - `mark_failed(self, *, delivery_id: uuid.UUID, error: str -> None)`
  - `mark_retrying(self, *, delivery_id: uuid.UUID, error: str | None=None -> None)`
  - `attach_outbox(self, *, delivery_id: uuid.UUID, outbox_event_id: uuid.UUID -> None)`

#### [backend/app/domain/repos/workforce_announcement_repo.py](backend/app/domain/repos/workforce_announcement_repo.py)

- Class `WorkforceAnnouncementRepo`
  - `__init__(self, db: AsyncSession)`
  - `exists_automation_dedupe(self, *, org_id: uuid.UUID, key: str -> bool)`
  - `get_by_id(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID -> WorkforceAnnouncement | None)`
  - `list_editor_view(self, *, org_id: uuid.UUID, include_archived: bool, limit: int=200 -> list[WorkforceAnnouncement])`
  - `list_published_visible(self, *, org_id: uuid.UUID, as_of: date, limit: int=200 -> list[WorkforceAnnouncement])`
  - `list_due_scheduled(self, *, now: datetime, limit: int=50 -> list[WorkforceAnnouncement])`
  - `create(self, row: WorkforceAnnouncement -> WorkforceAnnouncement)`
  - `update(self, row: WorkforceAnnouncement -> WorkforceAnnouncement)`
  - `get_receipt(self, *, announcement_id: uuid.UUID, user_id: uuid.UUID -> WorkforceAnnouncementReceipt | None)`
  - `upsert_receipt_read(self, *, announcement_id: uuid.UUID, user_id: uuid.UUID -> WorkforceAnnouncementReceipt)`
  - `upsert_receipt_ack(self, *, announcement_id: uuid.UUID, user_id: uuid.UUID -> WorkforceAnnouncementReceipt)`

#### [backend/app/domain/repos/workforce_announcement_template_repo.py](backend/app/domain/repos/workforce_announcement_template_repo.py)

- Class `WorkforceAnnouncementTemplateRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_by_org(self, *, org_id: uuid.UUID, include_inactive: bool=False, limit: int=200 -> list[WorkforceAnnouncementTemplate])`
  - `get_by_id(self, *, org_id: uuid.UUID, template_id: uuid.UUID -> WorkforceAnnouncementTemplate | None)`
  - `get_active_by_automation_key(self, *, org_id: uuid.UUID, automation_key: str -> WorkforceAnnouncementTemplate | None)`
  - `get_by_code(self, *, org_id: uuid.UUID, code: str -> WorkforceAnnouncementTemplate | None)`
  - `create(self, row: WorkforceAnnouncementTemplate -> WorkforceAnnouncementTemplate)`
  - `update(self, row: WorkforceAnnouncementTemplate -> WorkforceAnnouncementTemplate)`

#### [backend/app/domain/repos/workforce_attendance_repo.py](backend/app/domain/repos/workforce_attendance_repo.py)

- Class `WorkforceAttendanceRepo`
  - `__init__(self, db: AsyncSession)`
  - `get_record_for_date(self, *, org_id: uuid.UUID, employee_id: uuid.UUID, work_date: date -> WorkforceAttendanceRecord | None)`
  - `get_record(self, *, org_id: uuid.UUID, record_id: uuid.UUID -> WorkforceAttendanceRecord | None)`
  - `upsert_record(self, row: WorkforceAttendanceRecord -> WorkforceAttendanceRecord)`
  - `list_records(self, *, org_id: uuid.UUID, from_date: date, to_date: date, employee_id: uuid.UUID | None=None, status: str | None=None, limit: int=1000 -> list[WorkforceAttendanceRecord])`
  - `calendar_counts(self, *, org_id: uuid.UUID, from_date: date, to_date: date -> list[dict])`
  - `create_correction(self, row: WorkforceAttendanceCorrection -> WorkforceAttendanceCorrection)`
  - `get_correction(self, *, org_id: uuid.UUID, correction_id: uuid.UUID -> WorkforceAttendanceCorrection | None)`
  - `list_corrections(self, *, org_id: uuid.UUID, status: str | None=None, employee_id: uuid.UUID | None=None, limit: int=200 -> list[WorkforceAttendanceCorrection])`

#### [backend/app/domain/repos/workforce_department_repo.py](backend/app/domain/repos/workforce_department_repo.py)

- Class `WorkforceDepartmentRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_by_org(self, org_id: uuid.UUID, *, include_inactive: bool=False -> list[WorkforceDepartment])`
  - `get_by_id(self, *, org_id: uuid.UUID, department_id: uuid.UUID -> WorkforceDepartment | None)`
  - `get_by_name_or_code(self, *, org_id: uuid.UUID, name: str, code: str | None, exclude_department_id: uuid.UUID | None=None -> WorkforceDepartment | None)`
  - `create(self, row: WorkforceDepartment -> WorkforceDepartment)`

#### [backend/app/domain/repos/workforce_employee_repo.py](backend/app/domain/repos/workforce_employee_repo.py)

- Class `WorkforceEmployeeRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_by_org(self, *, org_id: uuid.UUID, include_inactive: bool=False, q: str | None=None, department_id: uuid.UUID | None=None, title_id: uuid.UUID | None=None, manager_employee_id: uuid.UUID | None=None, employment_status: str | None=None, limit: int=200 -> list[WorkforceEmployee])`
  - `get_by_id(self, *, org_id: uuid.UUID, employee_id: uuid.UUID -> WorkforceEmployee | None)`
  - `get_by_employee_code(self, *, org_id: uuid.UUID, employee_code: str, exclude_employee_id: uuid.UUID | None=None -> WorkforceEmployee | None)`
  - `create(self, row: WorkforceEmployee -> WorkforceEmployee)`
  - `get_by_email_ci(self, *, org_id: uuid.UUID, email: str -> WorkforceEmployee | None)`
  - `list_active_for_audience(self, *, org_id: uuid.UUID, audience_kind: str, audience_ids: list[uuid.UUID] -> list[WorkforceEmployee])`

#### [backend/app/domain/repos/workforce_hr_repo.py](backend/app/domain/repos/workforce_hr_repo.py)

- Class `WorkforceHrRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_policies(self, *, org_id: uuid.UUID, include_inactive: bool, limit: int=200 -> list[WorkforcePolicy])`
  - `get_policy(self, *, org_id: uuid.UUID, policy_id: uuid.UUID -> WorkforcePolicy | None)`
  - `create_policy(self, row: WorkforcePolicy -> WorkforcePolicy)`
  - `list_policy_acks(self, *, org_id: uuid.UUID, policy_id: uuid.UUID, limit: int=5000 -> list[WorkforcePolicyAcknowledgement])`
  - `get_ack(self, *, org_id: uuid.UUID, policy_id: uuid.UUID, employee_id: uuid.UUID -> WorkforcePolicyAcknowledgement | None)`
  - `upsert_ack(self, row: WorkforcePolicyAcknowledgement -> WorkforcePolicyAcknowledgement)`
  - `list_documents(self, *, org_id: uuid.UUID, employee_id: uuid.UUID | None, policy_id: uuid.UUID | None, include_inactive: bool, limit: int=500 -> list[WorkforceDocument])`
  - `create_document(self, row: WorkforceDocument -> WorkforceDocument)`
  - `deactivate_document(self, *, org_id: uuid.UUID, document_id: uuid.UUID -> WorkforceDocument | None)`
  - `list_checklist(self, *, org_id: uuid.UUID, employee_id: uuid.UUID | None, kind: str | None, include_done: bool, limit: int=5000 -> list[WorkforceChecklistItem])`
  - `get_checklist_item(self, *, org_id: uuid.UUID, item_id: uuid.UUID -> WorkforceChecklistItem | None)`
  - `create_checklist_item(self, row: WorkforceChecklistItem -> WorkforceChecklistItem)`
  - `set_checklist_done(self, *, org_id: uuid.UUID, item_id: uuid.UUID, done: bool, by_user_id: uuid.UUID | None, at: datetime | None -> WorkforceChecklistItem | None)`

#### [backend/app/domain/repos/workforce_leave_balance_repo.py](backend/app/domain/repos/workforce_leave_balance_repo.py)

- Class `WorkforceLeaveBalanceRepo`
  - `__init__(self, db: AsyncSession)`
  - `get_balance(self, *, org_id: uuid.UUID, employee_id: uuid.UUID, leave_type_id: uuid.UUID, year: int -> WorkforceLeaveBalance | None)`
  - `list_by_org(self, *, org_id: uuid.UUID, employee_id: uuid.UUID | None=None, year: int | None=None, limit: int=1000 -> list[WorkforceLeaveBalance])`
  - `upsert(self, row: WorkforceLeaveBalance -> WorkforceLeaveBalance)`

#### [backend/app/domain/repos/workforce_leave_request_repo.py](backend/app/domain/repos/workforce_leave_request_repo.py)

- `overlap_inclusive_calendar_days(a_start: date, a_end: date, b_start: date, b_end: date -> int)`
- Class `WorkforceLeaveRequestRepo`
  - `__init__(self, db: AsyncSession)`
  - `get_by_id(self, *, org_id: uuid.UUID, request_id: uuid.UUID -> WorkforceLeaveRequest | None)`
  - `list_by_org(self, *, org_id: uuid.UUID, status: str | None=None, employee_id: uuid.UUID | None=None, from_date: date | None=None, to_date: date | None=None, limit: int=200 -> list[WorkforceLeaveRequest])`
  - `has_overlapping_approved(self, *, org_id: uuid.UUID, employee_id: uuid.UUID, start_date: date, end_date: date, exclude_request_id: uuid.UUID | None=None -> bool)`
  - `create(self, row: WorkforceLeaveRequest -> WorkforceLeaveRequest)`
  - `update(self, row: WorkforceLeaveRequest -> WorkforceLeaveRequest)`
  - `sum_unpaid_leave_overlap_days_in_period(self, *, org_id: uuid.UUID, employee_id: uuid.UUID, period_start: date, period_end: date -> Decimal)`

#### [backend/app/domain/repos/workforce_leave_type_repo.py](backend/app/domain/repos/workforce_leave_type_repo.py)

- Class `WorkforceLeaveTypeRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_by_org(self, *, org_id: uuid.UUID, include_inactive: bool, limit: int=500 -> list[WorkforceLeaveType])`
  - `get_by_id(self, *, org_id: uuid.UUID, leave_type_id: uuid.UUID -> WorkforceLeaveType | None)`
  - `get_by_name_or_code(self, *, org_id: uuid.UUID, name: str, code: str | None -> WorkforceLeaveType | None)`
  - `create(self, row: WorkforceLeaveType -> WorkforceLeaveType)`
  - `update(self, row: WorkforceLeaveType -> WorkforceLeaveType)`

#### [backend/app/domain/repos/workforce_payroll_repo.py](backend/app/domain/repos/workforce_payroll_repo.py)

- Class `WorkforcePayrollRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_periods(self, *, org_id: uuid.UUID, limit: int=50 -> list[WorkforcePayrollPeriod])`
  - `get_period(self, *, org_id: uuid.UUID, period_id: uuid.UUID -> WorkforcePayrollPeriod | None)`
  - `create_period(self, row: WorkforcePayrollPeriod -> WorkforcePayrollPeriod)`
  - `update_period(self, row: WorkforcePayrollPeriod -> WorkforcePayrollPeriod)`
  - `list_entries(self, *, org_id: uuid.UUID, payroll_period_id: uuid.UUID, limit: int=5000 -> list[WorkforcePayrollEntry])`
  - `get_entry(self, *, org_id: uuid.UUID, entry_id: uuid.UUID -> WorkforcePayrollEntry | None)`
  - `get_entry_for_employee(self, *, org_id: uuid.UUID, payroll_period_id: uuid.UUID, employee_id: uuid.UUID -> WorkforcePayrollEntry | None)`
  - `upsert_entry(self, row: WorkforcePayrollEntry -> WorkforcePayrollEntry)`
  - `list_adjustments(self, *, org_id: uuid.UUID, payroll_entry_id: uuid.UUID, limit: int=500 -> list[WorkforcePayrollAdjustment])`
  - `create_adjustment(self, row: WorkforcePayrollAdjustment -> WorkforcePayrollAdjustment)`
  - `get_adjustment(self, *, org_id: uuid.UUID, adjustment_id: uuid.UUID -> WorkforcePayrollAdjustment | None)`
  - `delete_adjustment(self, row: WorkforcePayrollAdjustment -> None)`
  - `attendance_sum_for_employee(self, *, attendance_repo, org_id: uuid.UUID, employee_id: uuid.UUID, start_date: date, end_date: date -> tuple[int, int])`

#### [backend/app/domain/repos/workforce_shift_repo.py](backend/app/domain/repos/workforce_shift_repo.py)

- Class `WorkforceShiftRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_shifts(self, *, org_id: uuid.UUID, include_inactive: bool=False -> list[WorkforceShift])`
  - `get_shift(self, *, org_id: uuid.UUID, shift_id: uuid.UUID -> WorkforceShift | None)`
  - `get_shift_by_name(self, *, org_id: uuid.UUID, name: str, exclude_shift_id: uuid.UUID | None=None -> WorkforceShift | None)`
  - `create_shift(self, row: WorkforceShift -> WorkforceShift)`
  - `list_assignments(self, *, org_id: uuid.UUID, employee_id: uuid.UUID | None=None, shift_id: uuid.UUID | None=None, as_of: date | None=None, limit: int=200 -> list[WorkforceShiftAssignment])`
  - `get_assignment(self, *, org_id: uuid.UUID, assignment_id: uuid.UUID -> WorkforceShiftAssignment | None)`
  - `create_assignment(self, row: WorkforceShiftAssignment -> WorkforceShiftAssignment)`

#### [backend/app/domain/repos/workforce_title_repo.py](backend/app/domain/repos/workforce_title_repo.py)

- Class `WorkforceTitleRepo`
  - `__init__(self, db: AsyncSession)`
  - `list_by_org(self, org_id: uuid.UUID, *, include_inactive: bool=False -> list[WorkforceTitle])`
  - `get_by_id(self, *, org_id: uuid.UUID, title_id: uuid.UUID -> WorkforceTitle | None)`
  - `get_by_name(self, *, org_id: uuid.UUID, name: str, exclude_title_id: uuid.UUID | None=None -> WorkforceTitle | None)`
  - `create(self, row: WorkforceTitle -> WorkforceTitle)`

#### [backend/app/domain/services/__init__.py](backend/app/domain/services/__init__.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/domain/services/ai_chat_service.py](backend/app/domain/services/ai_chat_service.py)

- Class `AIChatService`
  - `__init__(self, chat_repo: AIChatRepo, analytics_repo: AnalyticsRepo, alerts_repo: AlertRepo, *, ai_service: AIService | None=None, db: AsyncSession | None=None)`
  - `create_session(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, title: str | None=None -> AIChatSession)`
  - `list_sessions(self, *, org_id: uuid.UUID, created_by_user_id: uuid.UUID | None=None, limit: int=50 -> list[AIChatSession])`
  - `get_session_with_messages(self, *, org_id: uuid.UUID, session_id: uuid.UUID, limit: int=100 -> tuple[AIChatSession, list[AIChatMessage]])`
  - `chat(self, *, org_id: uuid.UUID, session_id: uuid.UUID, actor_user_id: uuid.UUID, message: str, from_date, to_date -> AIChatMessage)`

#### [backend/app/domain/services/ai_grounding_validator.py](backend/app/domain/services/ai_grounding_validator.py)

- Class `AISemanticGroundingValidator`
  - `validate(self, summary: AISummaryResponse, metrics: dict -> list[str])`
  - `_parse_decimal(raw: str -> Decimal | None)`
  - `_collect_allowed_numbers(self, metrics: dict -> set[Decimal])`
  - `_collect_allowed_metric_terms(self, metrics: dict -> set[str])`
  - `_deep_collect_numbers(obj: object -> set[Decimal])`
  - `_matches_allowed_number(candidate: Decimal, allowed_numbers: set[Decimal] -> bool)`

#### [backend/app/domain/services/ai_service.py](backend/app/domain/services/ai_service.py)

- Class `AIChatGeneration`
- Class `AIService`
  - `__init__(self)`
  - `summary(self, metrics: dict -> AISummaryOut)`
  - `chat(self, user_message: str, metrics: dict -> AIChatGeneration)`
  - `_compose_chat_answer(*, user_message: str, summary: AISummaryResponse -> str)`

#### [backend/app/domain/services/alerts_refresh_service.py](backend/app/domain/services/alerts_refresh_service.py)

- Class `AlertRecalcEnqueueResult`
- Class `AlertRefreshService`
  - `__init__(self, job_repo: JobRepo)`
  - `enqueue_recalc(self, *, org_id: uuid.UUID, correlation_id: str | None=None, request_id: str | None=None, reason: str | None=None -> AlertRecalcEnqueueResult)`

#### [backend/app/domain/services/alerts_service.py](backend/app/domain/services/alerts_service.py)

- Class `AlertsService`
  - `__init__(self, db: AsyncSession, repo: AlertRepo, audit_repo: AuditRepo | None=None)`
  - `list_alerts(self, org_id, status, assigned_to_user_id=None, location_id=None)`
  - `_alert_rank_key(alert: Alert)`
  - `dismiss(self, alert)`
  - `_utc_now_naive( -> datetime)`
  - `assign(self, *, alert: Alert, assignee_user_id: uuid.UUID | None, actor_user_id: uuid.UUID)`
  - `acknowledge(self, *, alert: Alert)`
  - `detect_and_create(self, org_id)`
  - `_detect_workforce_missing_checkout(self, org_id: uuid.UUID -> int)`
  - `_detect_workforce_repeated_lateness(self, org_id: uuid.UUID -> int)`
  - `_detect_workforce_pending_leave(self, org_id: uuid.UUID -> int)`
  - `_detect_workforce_payroll_due(self, org_id: uuid.UUID -> int)`
  - `_detect_workforce_unpaid_payroll(self, org_id: uuid.UUID -> int)`
  - `_detect_workforce_high_absenteeism(self, org_id: uuid.UUID -> int)`
  - `_detect_workforce_overtime_threshold(self, org_id: uuid.UUID -> int)`
  - `_detect_workforce_contract_expiry(self, org_id: uuid.UUID -> int)`
  - `_detect_workforce_announcement_ack(self, org_id: uuid.UUID -> int)`
  - `_detection_contexts(self, org_id: uuid.UUID -> list[Location | None])`
  - `_create_if_new(self, alert: Alert, *, audit_action: str | None=None, audit_metadata: dict | None=None -> int)`
  - `_location_filters(location: Location | None -> list)`
  - `_location_suffix(location: Location | None -> str)`
  - `_location_meta(location: Location | None -> dict[str, str])`
  - `_detect_budget_threshold(self, org_id, threshold_pct: Decimal, *, location: Location | None)`
  - `_detect_inventory_stockout_risk(self, org_id, *, location: Location | None)`
  - `_detect_anomaly(self, org_id, spike_multiplier: Decimal, *, location: Location | None)`
  - `_robust_mad_score(history: list[Decimal], latest: Decimal -> Decimal | None)`
  - `_z_score(history: list[Decimal], latest: Decimal -> Decimal | None)`
  - `_detect_vendor_concentration(self, org_id, threshold_pct: Decimal, *, location: Location | None)`
  - `_detect_misc_growth(self, org_id, growth_multiplier: Decimal, *, location: Location | None)`
  - `_detect_margin_decline(self, org_id, *, location: Location | None)`
  - `_detect_subscription_creep(self, org_id, *, location: Location | None)`
  - `recompute(self, org_id)`

#### [backend/app/domain/services/analytics_service.py](backend/app/domain/services/analytics_service.py)

- Class `AnalyticsService`
  - `__init__(self, repo: AnalyticsRepo)`
  - `summary(self, org_id: uuid.UUID, from_date: date, to_date: date, *, location_id: uuid.UUID | None=None)`
  - `runway(self, org_id: uuid.UUID, lookback_months: int, conservative: bool, *, location_id: uuid.UUID | None=None)`
  - `recompute_monthly_aggregates(self, org_id, *, location_id: uuid.UUID | None=None -> int)`
  - `location_benchmark(self, org_id: uuid.UUID, from_date: date, to_date: date -> dict)`

#### [backend/app/domain/services/auth_service.py](backend/app/domain/services/auth_service.py)

- `_h(token: str -> str)`
- `_generate_confirmation_code( -> str)`
- `_generate_recovery_codes(count: int=10 -> list[str])`
- Class `AuthService`
  - `__init__(self, auth_repo: AuthRepo, org_repo: OrgRepo, audit_repo: AuditRepo, outbox_repo: OutboxRepo | None=None)`
  - `_issue_confirmation_token(self, *, user_id: uuid.UUID, email: str, dedupe_suffix: str -> str)`
  - `register(self, email: str, password: str)`
  - `resend_confirmation(self, email: str -> None)`
  - `login(self, email: str, password: str, request: Request, mfa_code: str | None=None, mfa_recovery_code: str | None=None -> TokenOut)`
  - `authenticate_for_reauth(self, *, user_id: uuid.UUID, password: str, mfa_code: str | None=None, mfa_recovery_code: str | None=None -> None)`
  - `_verify_mfa(self, *, user, mfa_code: str | None=None, mfa_recovery_code: str | None=None -> None)`
  - `issue_registration_tokens(self, user_id: uuid.UUID, request: Request -> TokenOut)`
  - `_issue_tokens(self, user_id: uuid.UUID, request: Request, audit_action: str | None=None -> TokenOut)`
  - `refresh(self, refresh_token: str, request: Request -> TokenOut)`
  - `logout(self, refresh_token: str, user_id: uuid.UUID | None -> None)`
  - `accept_invite(self, token: str, password: str)`
  - `confirm_registration(self, *, token: str | None=None, email: str | None=None, code: str | None=None)`
  - `register_invalid_code_attempt(self, *, email: str, code: str -> None)`
  - `setup_mfa(self, *, user_id: uuid.UUID, password: str -> tuple[str, str])`
  - `enable_mfa(self, *, user_id: uuid.UUID, code: str -> list[str])`
  - `disable_mfa(self, *, user_id: uuid.UUID, password: str, code: str -> None)`
  - `get_mfa_status(self, *, user_id: uuid.UUID -> dict)`
  - `regenerate_recovery_codes(self, *, user_id: uuid.UUID, password: str, code: str -> list[str])`
  - `list_sessions(self, *, user_id: uuid.UUID, current_refresh_token: str | None -> list[SessionOut])`
  - `revoke_session(self, *, user_id: uuid.UUID, session_id: uuid.UUID -> None)`
  - `revoke_other_sessions(self, *, user_id: uuid.UUID, current_refresh_token: str | None -> int)`

#### [backend/app/domain/services/bank_integration_service.py](backend/app/domain/services/bank_integration_service.py)

- Class `BankSyncStats`
- Class `BankIntegrationService`
  - `__init__(self, repo: BankRepo, audit_repo: AuditRepo, tx_repo: TransactionRepo, provider: BankProvider | None=None)`
  - `list_connections(self, org_id: uuid.UUID -> list[BankConnection])`
  - `list_accounts(self, org_id: uuid.UUID, connection_id: uuid.UUID -> list[BankAccount])`
  - `create_link_token(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID -> dict)`
  - `exchange_public_token(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, public_token: str, institution_name_override: str | None=None -> tuple[BankConnection, list[BankAccount]])`
  - `revoke_connection(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, connection_id: uuid.UUID -> BankConnection)`
  - `sync_connection(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, connection_id: uuid.UUID -> tuple[BankSyncRun, BankSyncStats])`
  - `_upsert_connection_from_exchange(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, exchange: ProviderExchangeResult, institution_name_override: str | None -> BankConnection)`

#### [backend/app/domain/services/bank_provider.py](backend/app/domain/services/bank_provider.py)

- Class `BankProviderError`
- Class `ProviderBankAccount`
- Class `ProviderExchangeResult`
- Class `ProviderTransaction`
- Class `ProviderSyncResult`
- Class `BankProvider`
  - `create_link_token(self, *, org_id: str, user_id: str -> dict)`
  - `exchange_public_token(self, *, public_token: str -> ProviderExchangeResult)`
  - `sync_transactions(self, *, access_token_ref: str, cursor: str | None -> ProviderSyncResult)`
- Class `StubBankProvider`
  - `create_link_token(self, *, org_id: str, user_id: str -> dict)`
  - `exchange_public_token(self, *, public_token: str -> ProviderExchangeResult)`
  - `sync_transactions(self, *, access_token_ref: str, cursor: str | None -> ProviderSyncResult)`
- Class `PlaidBankProvider`
  - `__init__(self, settings: Settings)`
  - `_resolve_base_url(env: str -> str)`
  - `_auth_payload(self -> dict)`
  - `_post(self, path: str, payload: dict -> dict)`
  - `create_link_token(self, *, org_id: str, user_id: str -> dict)`
  - `exchange_public_token(self, *, public_token: str -> ProviderExchangeResult)`
  - `sync_transactions(self, *, access_token_ref: str, cursor: str | None -> ProviderSyncResult)`
- `build_bank_provider(settings: Settings -> BankProvider)`
- `verify_plaid_webhook_signature(payload: bytes, signature: str | None, secret: str -> bool)`

#### [backend/app/domain/services/billing_service.py](backend/app/domain/services/billing_service.py)

- Class `BillingService`
  - `__init__(self, *, settings: Settings, org_repo: OrgRepo, audit_repo: AuditRepo, notification_repo: NotificationRepo)`
  - `_ensure_configured(self -> None)`
  - `_ensure_customer(self, billing: OrganizationBilling, *, org_name: str -> OrganizationBilling)`
  - `create_checkout_session(self, *, actor_user_id, org_name: str, billing: OrganizationBilling, price_id: str, success_url: str, cancel_url: str -> str)`
  - `create_portal_session(self, *, actor_user_id, org_name: str, billing: OrganizationBilling, return_url: str -> str)`
  - `sync_from_subscription(self, *, org_id, subscription_id: str | None, customer_id: str | None, status: str | None, price_id: str | None, current_period_end -> OrganizationBilling)`

#### [backend/app/domain/services/budget_service.py](backend/app/domain/services/budget_service.py)

- Class `BudgetVarianceLine`
- Class `BudgetService`
  - `__init__(self, repo: BudgetRepo)`
  - `_normalize_period_month(period_month: date -> date)`
  - `_month_end_exclusive(period_month: date -> date)`
  - `_normalize_budget_type(value: str | None -> str)`
  - `_normalize_category(value: str -> str)`
  - `list_budgets(self, *, org_id: uuid.UUID, period_month: date | None=None, budget_type: str | None=None, include_history: bool=False -> list[Budget])`
  - `create_budget(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, category: str, period_month: date, planned_amount: Decimal, budget_type: str='EXPENSE', notes: str | None=None -> Budget)`
  - `update_budget_version(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, budget_id: uuid.UUID, planned_amount: Decimal, notes: str | None=None -> Budget)`
  - `budget_variance(self, *, org_id: uuid.UUID, period_month: date, budget_type: str | None=None, location_id: uuid.UUID | None=None -> dict)`

#### [backend/app/domain/services/errors.py](backend/app/domain/services/errors.py)

- Class `AppError`
- Class `UnauthorizedError`
- Class `ForbiddenError`
- Class `NotFoundError`
- Class `ConflictError`
- Class `LimitExceededError`

#### [backend/app/domain/services/forecast_service.py](backend/app/domain/services/forecast_service.py)

- Class `ForecastService`
  - `__init__(self, forecast_repo: ForecastRepo, analytics_repo: AnalyticsRepo)`
  - `ensure_forecasts(self, org_id, months: int)`
  - `override(self, org_id, month: date, scenario: str, revenue_override, expense_override)`
  - `recompute(self, org_id, months: int=6 -> int)`

#### [backend/app/domain/services/idempotency_service.py](backend/app/domain/services/idempotency_service.py)

- Class `ReplayResult`
- Class `IdempotencyService`
  - `__init__(self, repo: IdempotencyRepo)`
  - `get_replay(self, *, org_id: uuid.UUID, user_id: uuid.UUID, endpoint: str, idempotency_key: str | None, request_hash: str -> ReplayResult | None)`
  - `store_response(self, *, org_id: uuid.UUID, user_id: uuid.UUID, endpoint: str, idempotency_key: str | None, request_hash: str, status_code: int, response_json: dict -> None)`

#### [backend/app/domain/services/import_profile_service.py](backend/app/domain/services/import_profile_service.py)

- Class `ImportProfileService`
  - `__init__(self, repo: ImportProfileRepo)`
  - `list_profiles(self, org_id: uuid.UUID, user_id: uuid.UUID -> list[ImportMappingProfile])`
  - `create_profile(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, name: str, column_map: dict, shared: bool -> ImportMappingProfile)`
  - `update_profile(self, *, profile_id: uuid.UUID, org_id: uuid.UUID, actor_user_id: uuid.UUID, name: str | None, column_map: dict | None, shared: bool | None -> ImportMappingProfile)`
  - `delete_profile(self, *, profile_id: uuid.UUID, org_id: uuid.UUID, actor_user_id: uuid.UUID -> None)`
  - `resolve_import_mapping(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, mapping: dict | None, profile_id: uuid.UUID | None -> tuple[dict, uuid.UUID | None])`
  - `_assert_editable(profile: ImportMappingProfile, actor_user_id: uuid.UUID -> None)`

#### [backend/app/domain/services/inventory_service.py](backend/app/domain/services/inventory_service.py)

- Class `ForecastLine`
- Class `InventoryService`
  - `__init__(self, repo: InventoryRepo)`
  - `_normalize_sku(sku: str -> str)`
  - `_normalize_name(name: str -> str)`
  - `_normalize_non_negative(value: Decimal, label: str, scale: str='0.001' -> Decimal)`
  - `_event_delta(event_type: str, quantity: Decimal -> Decimal)`
  - `list_items(self, *, org_id: uuid.UUID, include_inactive: bool=False, location_id: uuid.UUID | None=None -> list[InventoryItem])`
  - `create_item(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, sku: str, name: str, unit_cost: Decimal, reorder_point: Decimal, location_id: uuid.UUID | None=None, is_active: bool=True -> InventoryItem)`
  - `record_stock_event(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, item_id: uuid.UUID, event_type: str, quantity: Decimal, location_id: uuid.UUID | None=None, unit_cost: Decimal | None=None, occurred_at: datetime | None=None, reference: str | None=None, notes: str | None=None -> tuple[InventoryStockEvent, Decimal])`
  - `create_purchase_order(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, item_id: uuid.UUID, quantity: Decimal, expected_date: date, location_id: uuid.UUID | None=None, unit_cost: Decimal | None=None, external_ref: str | None=None, status: str='OPEN' -> InventoryPurchaseOrder)`
  - `forecast(self, *, org_id: uuid.UUID, lookback_days: int=30, horizon_days: int=30, location_id: uuid.UUID | None=None -> dict)`

#### [backend/app/domain/services/job_dispatch_service.py](backend/app/domain/services/job_dispatch_service.py)

- `retry_job_task(job: JobState)`

#### [backend/app/domain/services/location_service.py](backend/app/domain/services/location_service.py)

- Class `LocationService`
  - `__init__(self, repo: LocationRepo)`
  - `_normalize_name(name: str -> str)`
  - `_normalize_code(code: str | None -> str | None)`
  - `list_locations(self, org_id: uuid.UUID, *, include_inactive: bool=False -> list[Location])`
  - `create_location(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, name: str, code: str | None, is_active: bool=True -> Location)`
  - `update_location(self, *, org_id: uuid.UUID, location_id: uuid.UUID, name: str | None, code: str | None, is_active: bool | None -> Location)`
  - `deactivate_location(self, *, org_id: uuid.UUID, location_id: uuid.UUID -> Location)`
  - `ensure_org_location(self, *, org_id: uuid.UUID, location_id: uuid.UUID | None, require_active: bool=True -> Location | None)`

#### [backend/app/domain/services/notification_service.py](backend/app/domain/services/notification_service.py)

- Class `NotificationService`
  - `__init__(self, repo: NotificationRepo)`
  - `create_org_notification(self, *, org_id: uuid.UUID, category: str, title: str, message: str | None=None, link: str | None=None, metadata_json: dict | None=None -> None)`

#### [backend/app/domain/services/org_service.py](backend/app/domain/services/org_service.py)

- `_token_hash(token: str -> str)`
- Class `OrgService`
  - `__init__(self, org_repo: OrgRepo, auth_repo: AuthRepo, audit_repo: AuditRepo, outbox_repo: OutboxRepo | None=None)`
  - `_notify(self, *, org_id: uuid.UUID, category: str, title: str, message: str | None=None, link: str | None=None, metadata_json: dict | None=None -> None)`
  - `create_org(self, user_id: uuid.UUID, name: str)`
  - `list_orgs(self, user_id: uuid.UUID)`
  - `invite(self, actor_user_id: uuid.UUID, org_id: uuid.UUID, email: str, role: str -> str)`
  - `members(self, org_id: uuid.UUID)`
  - `get_settings(self, org_id: uuid.UUID)`
  - `update_settings(self, actor_user_id: uuid.UUID, org_id: uuid.UUID, body: OrgSettingsUpdateIn)`
  - `get_billing(self, org_id: uuid.UUID -> OrganizationBilling)`
  - `update_billing(self, actor_user_id: uuid.UUID, org_id: uuid.UUID, billing_email: str | None, invoice_enabled: bool | None, plan_label: str | None, billing_notes: str | None -> OrganizationBilling)`
- `require_role(actual: str, allowed: list[str])`

#### [backend/app/domain/services/payment_integration_service.py](backend/app/domain/services/payment_integration_service.py)

- Class `StripeWebhookIngestResult`
- Class `PaymentIntegrationService`
  - `__init__(self, repo: PaymentRepo, audit_repo: AuditRepo, *, settings: Any | None=None, stripe_secret_key: str='', stripe_webhook_secret: str='')`
  - `connect_stripe(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, provider_account_id: str | None, account_label: str | None=None)`
  - `list_connections(self, *, org_id: uuid.UUID, provider: str='STRIPE')`
  - `ingest_stripe_webhook(self, *, payload: bytes, signature_header: str | None -> StripeWebhookIngestResult)`
  - `reconcile(self, *, org_id: uuid.UUID, provider: str, date_from: date, date_to: date -> dict)`
  - `_normalize_event(self, event: Any -> dict[str, Any])`
  - `_construct_stripe_event(self, *, payload: bytes, signature_header: str | None -> dict[str, Any])`
  - `_resolve_org_and_connection(self, *, event: dict, obj: dict -> tuple[uuid.UUID | None, uuid.UUID | None])`
  - `_build_ledger_payload(self, *, event: dict, obj: dict, org_id: uuid.UUID | None, connection_id: uuid.UUID | None, webhook_event_id: uuid.UUID -> dict | None)`
  - `_map_event_to_entry(self, *, event_type: str, obj: dict -> tuple[str, int, str] | None)`

#### [backend/app/domain/services/privacy_service.py](backend/app/domain/services/privacy_service.py)

- Class `PrivacyService`
  - `__init__(self, db: AsyncSession, audit_repo: AuditRepo, deletion_repo: DeletionRepo)`
  - `request_account_deletion(self, *, user_id: uuid.UUID, reason: str | None -> dict)`
  - `list_account_deletion_requests(self, *, user_id: uuid.UUID, limit: int=20 -> list)`
  - `request_org_deletion(self, *, actor_user_id: uuid.UUID, org_id: uuid.UUID, reason: str | None -> dict)`
  - `list_org_deletion_requests(self, *, actor_user_id: uuid.UUID, org_id: uuid.UUID, limit: int=50 -> list)`
  - `rotate_org_pii(self, *, actor_user_id: uuid.UUID, org_id: uuid.UUID -> dict)`
  - `process_due_deletions(self, *, limit: int=100 -> dict)`
  - `_purge_user(self, user_id: uuid.UUID -> bool)`
  - `_purge_org(self, org_id: uuid.UUID -> bool)`
- `decrypt_invite_email(value: str -> str)`

#### [backend/app/domain/services/read_cache_service.py](backend/app/domain/services/read_cache_service.py)

- `alerts_cache_key(org_id: uuid.UUID, status: str | None, assignee_user_id: uuid.UUID | None=None, location_id: uuid.UUID | None=None -> str)`
- `alerts_cache_prefix(org_id: uuid.UUID -> str)`
- `analytics_summary_cache_key(org_id: uuid.UUID, from_date: date, to_date: date, location_id: uuid.UUID | None=None -> str)`
- `analytics_summary_cache_prefix(org_id: uuid.UUID -> str)`
- `transactions_cache_key(org_id: uuid.UUID, from_date: date | None, to_date: date | None, tx_type: str | None, category: str | None, q: str | None, page: int, page_size: int, location_id: uuid.UUID | None=None -> str)`
- `transactions_cache_prefix(org_id: uuid.UUID -> str)`
- `cache_get_json(key: str -> dict | list | None)`
- `cache_set_json(key: str, payload: dict | list, ttl_seconds: int -> None)`
- `cache_delete_prefix(prefix: str -> None)`

#### [backend/app/domain/services/report_service.py](backend/app/domain/services/report_service.py)

- Class `ReportService`
  - `__init__(self, repo: ReportRepo)`
  - `list_reports(self, org_id, *, location_id: uuid.UUID | None=None)`
  - `generate(self, org_id, week_start: date, created_by=None, *, location_id: uuid.UUID | None=None)`
  - `_enqueue_report_notification_outbox(self, report: Report -> None)`
  - `download_url(self, report: Report)`
  - `_build_context(self, org_id, week_start: date, week_end: date, *, location_id: uuid.UUID | None=None -> dict)`
  - `_fmt_money(value: Decimal | int | float -> str)`
  - `_build_pdf(self, org_id, week_start, week_end, context: dict -> bytes)`

#### [backend/app/domain/services/transaction_service.py](backend/app/domain/services/transaction_service.py)

- Class `TransactionService`
  - `__init__(self, tx_repo: TransactionRepo, audit_repo: AuditRepo, usage_service: UsageService | None=None, import_repo: ImportRepo | None=None, location_repo: LocationRepo | None=None)`
  - `_validate_location(self, org_id: uuid.UUID, location_id: uuid.UUID | None -> None)`
  - `_normalize_location_key(value: str | None -> str | None)`
  - `_resolve_location_mapping(self, org_id: uuid.UUID, rows: list[dict] -> list[uuid.UUID | None])`
  - `create(self, user_id: uuid.UUID, payload: TransactionCreateIn -> Transaction)`
  - `list(self, *args, **kwargs)`
  - `update(self, user_id: uuid.UUID, org_id: uuid.UUID, tx_id: uuid.UUID, payload: TransactionUpdateIn)`
  - `delete(self, user_id: uuid.UUID, org_id: uuid.UUID, tx_id: uuid.UUID)`
  - `_normalized_csv_rows(self, org_id: uuid.UUID, content: bytes, mapping: dict[str, str])`
  - `preview_csv(self, user_id: uuid.UUID, org_id: uuid.UUID, content: bytes, mapping: dict[str, str], file_name: str, mapping_profile_id: uuid.UUID | None=None)`
  - `import_csv(self, user_id: uuid.UUID, org_id: uuid.UUID, content: bytes, mapping: dict[str, str], file_name: str, mapping_profile_id: uuid.UUID | None=None)`
  - `bulk_remap_category(self, user_id: uuid.UUID, org_id: uuid.UUID, from_category: str, to_category: str, from_date: date | None=None, to_date: date | None=None -> int)`
  - `_create_import_record(self, *, user_id: uuid.UUID, org_id: uuid.UUID, file_name: str, status: str, total_rows: int, inserted_count: int, duplicate_count: int, error_rows: list[dict], mapping: dict[str, str], mapping_profile_id: uuid.UUID | None=None -> TransactionImport)`

#### [backend/app/domain/services/usage_service.py](backend/app/domain/services/usage_service.py)

- Class `UsageSnapshot`
- Class `UsageService`
  - `__init__(self, repo: PlanRepo)`
  - `ensure_plan(self, org_id: uuid.UUID -> OrganizationPlan)`
  - `consume(self, org_id: uuid.UUID, metric: str, delta: int=1 -> UsageSnapshot)`
  - `get_usage_overview(self, org_id: uuid.UUID -> dict)`
  - `_limit_for(plan: OrganizationPlan, metric: str -> int)`

#### [backend/app/domain/services/workforce_access_policy.py](backend/app/domain/services/workforce_access_policy.py)

- Class `WorkforceAccessScope`
  - `is_owner(self -> bool)`
  - `is_editor(self -> bool)`
  - `is_manager(self -> bool)`
  - `can_edit(self -> bool)`
  - `can_operate_team(self -> bool)`
  - `can_access_employee(self, employee_id: uuid.UUID -> bool)`
  - `should_redact_compensation(self -> bool)`
- `build_workforce_access_scope(*, db: AsyncSession, org_id: uuid.UUID, role: str, actor_user_id: uuid.UUID, actor_email: str -> WorkforceAccessScope)`

#### [backend/app/domain/services/workforce_announcement_automation.py](backend/app/domain/services/workforce_announcement_automation.py)

- `_render_template_text(template: str, variables: dict[str, str] -> str)`
- `try_emit_automation_announcement(db: AsyncSession, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, automation_key: str, dedupe_key: str, variables: dict[str, str] -> uuid.UUID | None)`

#### [backend/app/domain/services/workforce_announcement_service.py](backend/app/domain/services/workforce_announcement_service.py)

- `_parse_uuid_list(raw: list[Any] | None -> list[uuid.UUID])`
- `_normalize_attachments(raw: list[dict[str, Any]] | None -> list[dict[str, Any]] | None)`
- Class `WorkforceAnnouncementService`
  - `__init__(self, *, repo: WorkforceAnnouncementRepo, employee_repo: WorkforceEmployeeRepo, org_repo: OrgRepo, outbox_repo: OutboxRepo, delivery_repo: WorkforceAnnouncementDeliveryRepo, template_repo: WorkforceAnnouncementTemplateRepo)`
  - `_can_edit(role: str -> bool)`
  - `_validate_audience(self, *, kind: str, ids: list[uuid.UUID] -> tuple[str, list[uuid.UUID] | None])`
  - `_visible_to_member(row: WorkforceAnnouncement, *, user_email: str, emp: WorkforceEmployee | None -> bool)`
  - `_email_to_user_map(self, org_id: uuid.UUID -> dict[str, uuid.UUID])`
  - `_resolve_recipient_emails(self, *, org_id: uuid.UUID, row: WorkforceAnnouncement -> dict[str, uuid.UUID | None])`
  - `_enqueue_publish_emails(self, row: WorkforceAnnouncement -> None)`
  - `_ensure_template(self, *, org_id: uuid.UUID, template_id: uuid.UUID | None -> None)`
  - `list_for_user(self, *, org_id: uuid.UUID, user_id: uuid.UUID, user_email: str, role: str, include_archived: bool, limit: int=200 -> list[WorkforceAnnouncement])`
  - `create(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, title: str, body: str, priority: str, pinned: bool, acknowledgement_required: bool, expires_at: date | None, scheduled_publish_at: datetime | None, audience_kind: str='ORG_ALL', audience_ids: list[uuid.UUID] | None=None, attachments_json: list[dict[str, Any]] | None=None, send_email_on_publish: bool=False, template_id: uuid.UUID | None=None, automation_dedupe_key: str | None=None -> WorkforceAnnouncement)`
  - `update(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID, title: str | None=None, body: str | None=None, priority: str | None=None, pinned: bool | None=None, acknowledgement_required: bool | None=None, expires_at: date | None=None, expires_at_clear: bool=False, scheduled_publish_at: datetime | None=None, scheduled_publish_clear: bool=False, audience_kind: str | None=None, audience_ids: list[uuid.UUID] | None=None, audience_ids_clear: bool=False, attachments_json: list[dict[str, Any]] | None=None, attachments_clear: bool=False, send_email_on_publish: bool | None=None, template_id: uuid.UUID | None=None, template_clear: bool=False -> WorkforceAnnouncement)`
  - `publish(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID -> WorkforceAnnouncement)`
  - `archive(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID -> WorkforceAnnouncement)`
  - `get_and_mark_read(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID, user_id: uuid.UUID, user_email: str, role: str -> tuple[WorkforceAnnouncement, object | None])`
  - `acknowledge(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID, user_id: uuid.UUID, user_email: str -> object)`
  - `list_deliveries_page(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID, status: str | None, page: int, page_size: int -> tuple[list, int])`
- Class `WorkforceAnnouncementTemplateService`
  - `__init__(self, *, repo: WorkforceAnnouncementTemplateRepo)`
  - `list_templates(self, *, org_id: uuid.UUID, include_inactive: bool=False -> list[WorkforceAnnouncementTemplate])`
  - `create(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, name: str, body_template: str, code: str | None=None, description: str | None=None, automation_key: str | None=None -> WorkforceAnnouncementTemplate)`
  - `update(self, *, org_id: uuid.UUID, template_id: uuid.UUID, name: str | None=None, body_template: str | None=None, code: str | None=None, code_clear: bool=False, description: str | None=None, description_clear: bool=False, automation_key: str | None=None, automation_clear: bool=False, is_active: bool | None=None -> WorkforceAnnouncementTemplate)`
- `build_workforce_announcement_service(db -> WorkforceAnnouncementService)`
- `build_workforce_announcement_template_service(db -> WorkforceAnnouncementTemplateService)`

#### [backend/app/domain/services/workforce_attendance_service.py](backend/app/domain/services/workforce_attendance_service.py)

- Class `AttendanceDerived`
- Class `WorkforceAttendanceService`
  - `__init__(self, *, attendance_repo: WorkforceAttendanceRepo, employee_repo: WorkforceEmployeeRepo, shift_repo: WorkforceShiftRepo)`
  - `_work_date_for(at: datetime -> date)`
  - `_normalize_status(status: str -> str)`
  - `_quantize_hours(minutes: int -> Decimal)`
  - `_resolve_shift_for_date(self, *, org_id: uuid.UUID, employee_id: uuid.UUID, work_date: date -> tuple[uuid.UUID | None, uuid.UUID | None, time | None, time | None, int])`
  - `_derive(self, *, status: str, clock_in_at: datetime | None, clock_out_at: datetime | None, expected_start: datetime | None, grace_minutes: int -> AttendanceDerived)`
  - `clock_in(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, employee_id: uuid.UUID, at: datetime | None=None -> WorkforceAttendanceRecord)`
  - `clock_out(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, employee_id: uuid.UUID, at: datetime | None=None -> WorkforceAttendanceRecord)`
  - `manual_entry(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, employee_id: uuid.UUID, work_date: date, status: str, clock_in_at: datetime | None, clock_out_at: datetime | None, notes: str | None -> WorkforceAttendanceRecord)`
  - `daily_view(self, *, org_id: uuid.UUID, day: date, employee_id: uuid.UUID | None=None -> list[WorkforceAttendanceRecord])`
  - `calendar_month(self, *, org_id: uuid.UUID, month: str -> dict)`
  - `request_correction(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, attendance_record_id: uuid.UUID, reason: str, proposed_clock_in_at: datetime | None, proposed_clock_out_at: datetime | None, proposed_status: str | None -> WorkforceAttendanceCorrection)`
  - `review_correction(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, correction_id: uuid.UUID, status: str, reviewer_note: str | None -> WorkforceAttendanceCorrection)`

#### [backend/app/domain/services/workforce_department_service.py](backend/app/domain/services/workforce_department_service.py)

- Class `WorkforceDepartmentService`
  - `__init__(self, repo: WorkforceDepartmentRepo)`
  - `_normalize_name(name: str -> str)`
  - `_normalize_code(code: str | None -> str | None)`
  - `list_departments(self, *, org_id: uuid.UUID, include_inactive: bool=False -> list[WorkforceDepartment])`
  - `create_department(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, name: str, code: str | None, is_active: bool=True -> WorkforceDepartment)`
  - `update_department(self, *, org_id: uuid.UUID, department_id: uuid.UUID, name: str | None, code: str | None, is_active: bool | None -> WorkforceDepartment)`
  - `deactivate_department(self, *, org_id: uuid.UUID, department_id: uuid.UUID -> WorkforceDepartment)`

#### [backend/app/domain/services/workforce_employee_service.py](backend/app/domain/services/workforce_employee_service.py)

- Class `WorkforceEmployeeService`
  - `__init__(self, *, employee_repo: WorkforceEmployeeRepo, department_repo: WorkforceDepartmentRepo, title_repo: WorkforceTitleRepo)`
  - `_normalize_name(value: str, label: str -> str)`
  - `_normalize_employee_code(code: str | None -> str | None)`
  - `_normalize_email(email: str | None -> str | None)`
  - `_normalize_phone(phone: str | None -> str | None)`
  - `_normalize_money(value: Decimal | None, label: str -> Decimal | None)`
  - `_validate_dates(start_date: date | None, end_date: date | None -> None)`
  - `_validate_contract(contract_start: date | None, contract_end: date | None -> None)`
  - `list_employees(self, *, org_id: uuid.UUID, include_inactive: bool=False, q: str | None=None, department_id: uuid.UUID | None=None, title_id: uuid.UUID | None=None, manager_employee_id: uuid.UUID | None=None, employment_status: str | None=None, limit: int=200 -> list[WorkforceEmployee])`
  - `get_employee(self, *, org_id: uuid.UUID, employee_id: uuid.UUID -> WorkforceEmployee)`
  - `create_employee(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, employee_code: str | None, first_name: str, last_name: str, email: str | None, phone: str | None, department_id: uuid.UUID | None, title_id: uuid.UUID | None, manager_employee_id: uuid.UUID | None, location_id: uuid.UUID | None, employment_type: str, employment_status: str, start_date: date | None, end_date: date | None, contract_start: date | None, contract_end: date | None, probation_end: date | None, salary_type: str, base_salary: Decimal | None, hourly_rate: Decimal | None, is_active: bool=True -> WorkforceEmployee)`
  - `update_employee(self, *, org_id: uuid.UUID, employee_id: uuid.UUID, fields_set: set[str], employee_code: str | None, first_name: str | None, last_name: str | None, email: str | None, phone: str | None, department_id: uuid.UUID | None, title_id: uuid.UUID | None, manager_employee_id: uuid.UUID | None, location_id: uuid.UUID | None, employment_type: str | None, employment_status: str | None, start_date: date | None, end_date: date | None, contract_start: date | None, contract_end: date | None, probation_end: date | None, salary_type: str | None, base_salary: Decimal | None, hourly_rate: Decimal | None, is_active: bool | None -> WorkforceEmployee)`
  - `deactivate_employee(self, *, org_id: uuid.UUID, employee_id: uuid.UUID -> WorkforceEmployee)`

#### [backend/app/domain/services/workforce_hr_service.py](backend/app/domain/services/workforce_hr_service.py)

- Class `WorkforceHrService`
  - `__init__(self, *, hr_repo: WorkforceHrRepo, employee_repo: WorkforceEmployeeRepo)`
  - `_normalize_code(code: str -> str)`
  - `_normalize_title(value: str, label: str='Title' -> str)`
  - `_normalize_kind(kind: str -> str)`
  - `list_policies(self, *, org_id: uuid.UUID, include_inactive: bool, limit: int=200 -> list[WorkforcePolicy])`
  - `create_policy(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, code: str, title: str, body: str, requires_ack: bool, publish_now: bool, is_active: bool=True -> WorkforcePolicy)`
  - `publish_policy(self, *, org_id: uuid.UUID, policy_id: uuid.UUID -> WorkforcePolicy)`
  - `acknowledge_policy_for_employee(self, *, org_id: uuid.UUID, policy_id: uuid.UUID, employee_id: uuid.UUID, actor_user_id: uuid.UUID -> WorkforcePolicyAcknowledgement)`
  - `list_policy_acks(self, *, org_id: uuid.UUID, policy_id: uuid.UUID, limit: int=5000 -> list[WorkforcePolicyAcknowledgement])`
  - `list_documents(self, *, org_id: uuid.UUID, employee_id: uuid.UUID | None, policy_id: uuid.UUID | None, include_inactive: bool, limit: int=500 -> list[WorkforceDocument])`
  - `create_document(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, employee_id: uuid.UUID | None, policy_id: uuid.UUID | None, name: str, content_type: str, size_bytes: int, object_key: str, url: str -> WorkforceDocument)`
  - `deactivate_document(self, *, org_id: uuid.UUID, document_id: uuid.UUID -> WorkforceDocument)`
  - `list_checklist(self, *, org_id: uuid.UUID, employee_id: uuid.UUID | None, kind: str | None, include_done: bool, limit: int=5000 -> list[WorkforceChecklistItem])`
  - `create_checklist_item(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, employee_id: uuid.UUID, kind: str, title: str, details: str | None, due_date: date | None -> WorkforceChecklistItem)`
  - `set_checklist_done(self, *, org_id: uuid.UUID, item_id: uuid.UUID, done: bool, actor_user_id: uuid.UUID -> WorkforceChecklistItem)`

#### [backend/app/domain/services/workforce_intelligence_service.py](backend/app/domain/services/workforce_intelligence_service.py)

- Class `WorkforceIntelligenceService`
  - `__init__(self, db: AsyncSession)`
  - `dashboard_intelligence(self, *, org_id: uuid.UUID, as_of: date -> WorkforceDashboardIntelOut)`
  - `reports_summary(self, *, org_id: uuid.UUID, from_date: date, to_date: date -> WorkforceReportsSummaryOut)`

#### [backend/app/domain/services/workforce_leave_service.py](backend/app/domain/services/workforce_leave_service.py)

- `_norm_code(code: str | None -> str | None)`
- Class `WorkforceLeaveService`
  - `__init__(self, *, leave_type_repo: WorkforceLeaveTypeRepo, leave_balance_repo: WorkforceLeaveBalanceRepo, leave_request_repo: WorkforceLeaveRequestRepo, employee_repo: WorkforceEmployeeRepo, attendance_repo: WorkforceAttendanceRepo)`
  - `list_leave_types(self, *, org_id: uuid.UUID, include_inactive: bool -> list[WorkforceLeaveType])`
  - `create_leave_type(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, name: str, code: str | None, is_paid: bool, requires_approval: bool, is_active: bool -> WorkforceLeaveType)`
  - `update_leave_type(self, *, org_id: uuid.UUID, leave_type_id: uuid.UUID, name: str | None, code: str | None, is_paid: bool | None, requires_approval: bool | None, is_active: bool | None -> WorkforceLeaveType)`
  - `deactivate_leave_type(self, *, org_id: uuid.UUID, leave_type_id: uuid.UUID -> WorkforceLeaveType)`
  - `list_balances(self, *, org_id: uuid.UUID, employee_id: uuid.UUID | None, year: int | None, limit: int=2000 -> list[WorkforceLeaveBalance])`
  - `allocate_balance(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, employee_id: uuid.UUID, leave_type_id: uuid.UUID, year: int, allocated_days: Decimal -> WorkforceLeaveBalance)`
  - `list_requests(self, *, org_id: uuid.UUID, status: str | None, employee_id: uuid.UUID | None, from_date: date | None, to_date: date | None, limit: int -> list[WorkforceLeaveRequest])`
  - `create_request(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, employee_id: uuid.UUID, leave_type_id: uuid.UUID, start_date: date, end_date: date, days: Decimal, reason: str | None -> WorkforceLeaveRequest)`
  - `decide_request(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, request_id: uuid.UUID, status: str, reviewer_note: str | None -> WorkforceLeaveRequest)`
  - `_apply_decision(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, request: WorkforceLeaveRequest, decision: str, note: str | None -> None)`

#### [backend/app/domain/services/workforce_payroll_service.py](backend/app/domain/services/workforce_payroll_service.py)

- `_q2(value: Decimal -> Decimal)`
- Class `PayrollTotals`
- Class `WorkforcePayrollService`
  - `__init__(self, *, payroll_repo: WorkforcePayrollRepo, employee_repo: WorkforceEmployeeRepo, attendance_repo: WorkforceAttendanceRepo, leave_request_repo: WorkforceLeaveRequestRepo)`
  - `list_periods(self, *, org_id: uuid.UUID, limit: int=50 -> list[WorkforcePayrollPeriod])`
  - `create_period(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, start_date: date, end_date: date -> WorkforcePayrollPeriod)`
  - `generate_draft(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, payroll_period_id: uuid.UUID, include_inactive_employees: bool, overtime_multiplier: Decimal -> list[WorkforcePayrollEntry])`
  - `_salaried_unpaid_leave_deduction(self, *, org_id: uuid.UUID, employee_id: uuid.UUID, period_start: date, period_end: date, base_salary: Decimal -> Decimal)`
  - `_compute_totals(self, *, entry: WorkforcePayrollEntry, adjustments: list[WorkforcePayrollAdjustment] -> PayrollTotals)`
  - `list_entries(self, *, org_id: uuid.UUID, payroll_period_id: uuid.UUID -> list[WorkforcePayrollEntry])`
  - `create_adjustment(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, payroll_period_id: uuid.UUID, payroll_entry_id: uuid.UUID, employee_id: uuid.UUID, kind: str, amount: Decimal, label: str | None, notes: str | None -> WorkforcePayrollAdjustment)`
  - `delete_adjustment(self, *, org_id: uuid.UUID, payroll_period_id: uuid.UUID, adjustment_id: uuid.UUID -> None)`
  - `approve_period(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, payroll_period_id: uuid.UUID -> WorkforcePayrollPeriod)`
  - `mark_paid(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, payroll_period_id: uuid.UUID -> WorkforcePayrollPeriod)`
  - `export_csv(self, *, org_id: uuid.UUID, payroll_period_id: uuid.UUID, redact_amounts: bool=False -> str)`

#### [backend/app/domain/services/workforce_payslip_pdf.py](backend/app/domain/services/workforce_payslip_pdf.py)

- `_fmt_money(value: Decimal | None, *, redact: bool -> str)`
- `_fmt_hours(value: Decimal | None, *, redact: bool -> str)`
- `build_workforce_payslip_pdf_bytes(*, employee_name: str, redact: bool, entry: WorkforcePayrollEntry, period: WorkforcePayrollPeriod, adjustments: list[WorkforcePayrollAdjustment] -> bytes)`

#### [backend/app/domain/services/workforce_shift_service.py](backend/app/domain/services/workforce_shift_service.py)

- Class `WorkforceShiftService`
  - `__init__(self, *, shift_repo: WorkforceShiftRepo, employee_repo: WorkforceEmployeeRepo)`
  - `_normalize_name(name: str -> str)`
  - `_validate_times(start_time: time, end_time: time -> None)`
  - `list_shifts(self, *, org_id: uuid.UUID, include_inactive: bool=False -> list[WorkforceShift])`
  - `create_shift(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, name: str, start_time: time, end_time: time, grace_minutes: int, is_active: bool=True -> WorkforceShift)`
  - `update_shift(self, *, org_id: uuid.UUID, shift_id: uuid.UUID, name: str | None, start_time: time | None, end_time: time | None, grace_minutes: int | None, is_active: bool | None -> WorkforceShift)`
  - `deactivate_shift(self, *, org_id: uuid.UUID, shift_id: uuid.UUID -> WorkforceShift)`
  - `list_assignments(self, *, org_id: uuid.UUID, employee_id: uuid.UUID | None=None, shift_id: uuid.UUID | None=None, as_of: date | None=None, limit: int=200 -> list[WorkforceShiftAssignment])`
  - `assign_shift(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, employee_id: uuid.UUID, shift_id: uuid.UUID, effective_from: date, effective_to: date | None -> WorkforceShiftAssignment)`

#### [backend/app/domain/services/workforce_title_service.py](backend/app/domain/services/workforce_title_service.py)

- Class `WorkforceTitleService`
  - `__init__(self, repo: WorkforceTitleRepo)`
  - `_normalize_name(name: str -> str)`
  - `list_titles(self, *, org_id: uuid.UUID, include_inactive: bool=False -> list[WorkforceTitle])`
  - `create_title(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, name: str, level: int | None, is_active: bool=True -> WorkforceTitle)`
  - `update_title(self, *, org_id: uuid.UUID, title_id: uuid.UUID, name: str | None, level: int | None, is_active: bool | None -> WorkforceTitle)`
  - `deactivate_title(self, *, org_id: uuid.UUID, title_id: uuid.UUID -> WorkforceTitle)`

#### [backend/app/infra/__init__.py](backend/app/infra/__init__.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/infra/ai_client.py](backend/app/infra/ai_client.py)

- `generate_summary_stub(metrics: dict -> AISummaryResponse)`
- `generate_summary(metrics: dict -> AISummaryResponse)`
- `get_ai_provider_health(*, live_check: bool=False -> dict[str, object])`
- `_generate_summary_openai(metrics: dict -> AISummaryResponse)`
- `_generate_summary_ollama_server(metrics: dict -> AISummaryResponse)`
- `_build_ollama_summary_prompt(metrics: dict -> str)`
- `_build_ollama_repair_prompt(metrics: dict, raw_output: str -> str)`
- `_call_ollama_server_prompt(prompt: str -> str)`
- `_extract_ai_text(body: object -> str)`
- `_extract_json_object(text: str -> dict)`
- `_try_parse_json_dict(candidate: str -> dict | None)`
- `_parse_relaxed_summary(text: str -> dict | None)`
- `_clean_relaxed_value(raw: str -> str)`
- `_split_relaxed_list(raw: str -> list[str])`
- `_normalize_summary_payload(raw: dict -> dict)`
- `_normalize_string(value: object, *, fallback: str -> str)`
- `_normalize_string_list(value: object, *, fallback: list[str] -> list[str])`
- `_normalize_confidence(value: object -> str)`
- `_safe_excerpt(text: str, *, max_len: int=400 -> str)`
- `_openai_live_health_check( -> None)`
- `_ollama_server_live_health_check( -> None)`

#### [backend/app/infra/cache.py](backend/app/infra/cache.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/infra/email.py](backend/app/infra/email.py)

- Class `SendEmailResult`
- `_render_from_header( -> str)`
- `_send_smtp(*, to: str, subject: str, body_text: str, body_html: str | None -> SendEmailResult)`
- `_send_resend(*, to: str, subject: str, body_text: str, body_html: str | None -> SendEmailResult)`
- `send_email(to: str, subject: str, body: str, *, html_body: str | None=None -> SendEmailResult)`

#### [backend/app/infra/s3.py](backend/app/infra/s3.py)

- `s3_client()`
- `ensure_bucket(client -> None)`

#### [backend/app/jobs/__init__.py](backend/app/jobs/__init__.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/jobs/async_runtime.py](backend/app/jobs/async_runtime.py)

- `_start_loop_for_pid(pid: int -> asyncio.AbstractEventLoop)`
- `_get_loop( -> asyncio.AbstractEventLoop)`
- `run_async(awaitable: Awaitable[T] -> T)`

#### [backend/app/jobs/beat_schedule.py](backend/app/jobs/beat_schedule.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/jobs/celery_app.py](backend/app/jobs/celery_app.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/jobs/task_tracking.py](backend/app/jobs/task_tracking.py)

- `_traceback_summary(exc: Exception -> str)`
- `_request_header(task: Task, key: str -> str | None)`
- `_task_id(task: Task -> str)`
- `mark_running(*, task_id: str, request_id: str | None, org_id: str | None, task_name: str, dedupe_key: str, payload: dict, correlation_id: str | None -> str)`
- `mark_succeeded(task_id: str, result: dict | None=None -> None)`
- `mark_retrying(task_id: str, *, retry_count: int, error: Exception -> None)`
- `mark_failed(task_id: str, *, retry_count: int, error: Exception -> None)`
- `run_tracked_task(task: Task, *, org_id: str | None, task_name: str, dedupe_key: str, payload: dict, correlation_id: str | None, max_retries: int, runner, result_payload_builder)`

#### [backend/app/jobs/tasks/__init__.py](backend/app/jobs/tasks/__init__.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/jobs/tasks/admin.py](backend/app/jobs/tasks/admin.py)

- `recompute_monthly_aggregates(self, org_id: str, correlation_id: str | None=None)`
- `_recompute_aggregates(org_id: str -> int)`
- `recompute_forecasts(self, org_id: str, correlation_id: str | None=None)`
- `_recompute_forecasts(org_id: str -> int)`
- `recompute_alerts(self, org_id: str, correlation_id: str | None=None)`
- `_recompute_alerts(org_id: str -> int)`
- `verify_report_objects(self, org_id: str, correlation_id: str | None=None)`
- `_verify_report_objects(org_id: str -> dict)`

#### [backend/app/jobs/tasks/alerts.py](backend/app/jobs/tasks/alerts.py)

- `recalc_alerts(self, org_id: str, correlation_id: str | None=None)`
- `_recalc(org_id: str, correlation_id: str | None=None)`

#### [backend/app/jobs/tasks/analytics.py](backend/app/jobs/tasks/analytics.py)

- `recompute_org_analytics(self, org_id: str, correlation_id: str | None=None)`
- `_recompute(org_id: str, correlation_id: str | None=None -> dict)`

#### [backend/app/jobs/tasks/banks.py](backend/app/jobs/tasks/banks.py)

- `sync_bank_connection(self, org_id: str, connection_id: str, actor_user_id: str | None=None, correlation_id: str | None=None)`
- `_sync(org_id: str, connection_id: str, actor_user_id: str | None=None -> dict)`
- `sync_all_active_bank_connections(self, correlation_id: str | None=None)`
- `_sync_all_active( -> dict)`

#### [backend/app/jobs/tasks/emails.py](backend/app/jobs/tasks/emails.py)

- `send_email_task(self, to: str, subject: str, body: str, correlation_id: str | None=None)`
- `_send(to: str, subject: str, body: str, correlation_id: str | None=None)`

#### [backend/app/jobs/tasks/forecasts.py](backend/app/jobs/tasks/forecasts.py)

- `recalc_forecasts(self, org_id: str, correlation_id: str | None=None)`
- `_recalc(org_id: str, correlation_id: str | None=None)`

#### [backend/app/jobs/tasks/outbox.py](backend/app/jobs/tasks/outbox.py)

- `process_outbox(self, batch_size: int=100, correlation_id: str | None=None)`
- `_process(batch_size: int, correlation_id: str | None=None -> int)`

#### [backend/app/jobs/tasks/privacy.py](backend/app/jobs/tasks/privacy.py)

- `purge_deletion_requests(self, correlation_id: str | None=None)`
- `_purge_deletions( -> dict)`

#### [backend/app/jobs/tasks/reports.py](backend/app/jobs/tasks/reports.py)

- `generate_weekly_report(self, org_id: str, week_start: str, created_by: str | None=None, correlation_id: str | None=None, location_id: str | None=None)`
- `_generate(org_id: str, week_start: str, created_by: str | None=None, correlation_id: str | None=None, location_id: str | None=None)`
- `generate_all_org_reports(self)`
- `_for_all()`

#### [backend/app/jobs/tasks/workforce.py](backend/app/jobs/tasks/workforce.py)

- `publish_due_workforce_announcements(self, batch_size: int=50, correlation_id: str | None=None)`
- `_run_publish_due(batch_size: int, correlation_id: str | None -> int)`

#### [backend/app/main.py](backend/app/main.py)

- `app_error_handler(request: Request, exc: AppError)`
- `http_exception_handler(request: Request, exc: StarletteHTTPException)`
- `validation_exception_handler(request: Request, exc: RequestValidationError)`

#### [backend/app/scripts_seed_categories.py](backend/app/scripts_seed_categories.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/utils/__init__.py](backend/app/utils/__init__.py)

Module wiring, constants or registration imports; inspect source.

#### [backend/app/utils/csv_import.py](backend/app/utils/csv_import.py)

- `_normalize_type(value: str -> str)`
- `parse_csv(content: bytes, mapping: dict[str, str], max_bytes: int -> list[dict])`

#### [backend/app/utils/idempotency.py](backend/app/utils/idempotency.py)

- `report_key(org_id: str, week_start: date, location_id: uuid.UUID | None=None -> str)`

#### [backend/app/utils/idempotency_request.py](backend/app/utils/idempotency_request.py)

- `_json_default(value: object -> str)`
- `request_hash(payload: dict -> str)`
- `bytes_sha256(payload: bytes -> str)`

#### [backend/app/utils/money.py](backend/app/utils/money.py)

- `q(value: Decimal -> Decimal)`

#### [backend/app/utils/time.py](backend/app/utils/time.py)

- `utc_now( -> datetime)`
- `month_start(d: date -> date)`

#### [backend/scripts/migration_safety_check.py](backend/scripts/migration_safety_check.py)

- `_run(*args: str -> str)`
- `_head_revisions( -> list[str])`
- `_assert_single_head( -> str)`
- `main( -> int)`

#### [scripts/loadtest/bootstrap_multi_org_perf.py](scripts/loadtest/bootstrap_multi_org_perf.py)

- `_normalize_db_url(raw: str | None -> str)`
- `_fetch_confirmation_token(email: str -> str)`
- `parse_args( -> argparse.Namespace)`
- `main( -> None)`

#### [scripts/loadtest/bootstrap_perf.py](scripts/loadtest/bootstrap_perf.py)

- `_normalize_db_url(raw: str | None -> str)`
- `_fetch_confirmation_token(email: str -> str)`
- `main( -> None)`

#### [scripts/loadtest/evaluate_perf_gates.py](scripts/loadtest/evaluate_perf_gates.py)

- `_load_json(path: Path -> dict[str, Any])`
- `_metric_value(summary: dict[str, Any], metric_key: str, stat_key: str, default: float=0.0 -> float)`
- `_read_metrics(summary: dict[str, Any], endpoints: dict[str, int] -> dict[str, float])`
- `_is_breach(metrics: dict[str, float], failure_rate_max: float, p95_thresholds: dict[str, int] -> bool)`
- `_write_markdown(path: Path, payload: dict[str, Any] -> None)`
- `main( -> int)`

#### [scripts/ops/secret_hygiene_audit.py](scripts/ops/secret_hygiene_audit.py)

- Class `Finding`
  - `as_dict(self -> dict[str, str])`
- `parse_env_file(path: Path -> dict[str, str])`
- `is_placeholder(value: str -> bool)`
- `should_skip(path: Path -> bool)`
- `scan_files(root: Path -> list[Finding])`
- `build_markdown_report(report: dict[str, object] -> str)`
- `main( -> int)`

#### [scripts/ops/verify_ai_live_mode.py](scripts/ops/verify_ai_live_mode.py)

- `_normalize_db_url(raw: str | None -> str)`
- `_fetch_confirmation_token(database_url: str, email: str, timeout_seconds: int=12 -> str)`
- `_run_fallback_test(pytest_target: str -> dict[str, object])`
- `main( -> int)`

#### [scripts/seed_load_dataset.py](scripts/seed_load_dataset.py)

- `parse_args( -> argparse.Namespace)`
- `_rand_amount(is_expense: bool -> Decimal)`
- `_load_org_ids(args: argparse.Namespace -> list[uuid.UUID])`
- `main( -> None)`

#### [scripts/smoke_mvp.py](scripts/smoke_mvp.py)

- `_mutating_headers(auth_mode: str, token: str | None, client: httpx.Client, csrf_cookie_name: str, csrf_header_name: str -> dict[str, str])`
- `run(base_url: str, csv_path: Path, auth_mode: str='bearer', csrf_cookie_name: str='ai_coo_csrf_token', csrf_header_name: str='X-CSRF-Token', seeded_email: str | None=None, seeded_password: str | None=None, seeded_org_id: str | None=None -> None)`
- `main( -> None)`

#### [scripts/smoke_workforce_intelligence.py](scripts/smoke_workforce_intelligence.py)

- `_mutating_headers(auth_mode: str, token: str | None, client: httpx.Client, csrf_cookie_name: str, csrf_header_name: str -> dict[str, str])`
- `run(*, base_url: str, auth_mode: str, csrf_cookie_name: str, csrf_header_name: str, seeded_email: str | None, seeded_password: str | None, seeded_org_id: str | None, as_of: str | None -> None)`
- `main( -> None)`

#### [scripts/verify_runtime.py](scripts/verify_runtime.py)

- `_run(cmd: list[str], cwd: Path, env: dict[str, str] | None=None -> None)`
- `_wait_for_health(health_url: str, timeout_sec: int -> None)`
- `_npm_cmd( -> str)`
- `_resolve_python(root: Path -> Path)`
- `_cookie_mode_enabled( -> bool)`
- `main( -> None)`

### F. Migration sequence

| Revision | Previous revision | Purpose | Source |
| --- | --- | --- | --- |
| `0001_initial` | `None` | Initial | [backend/migrations/versions/0001_initial.py](backend/migrations/versions/0001_initial.py) |
| `0002_categories` | `0001_initial` | Categories | [backend/migrations/versions/0002_categories.py](backend/migrations/versions/0002_categories.py) |
| `0003_job_states` | `0002_categories` | Job states | [backend/migrations/versions/0003_job_states.py](backend/migrations/versions/0003_job_states.py) |
| `0004_invites_and_org_thresholds` | `0003_job_states` | Invites and org thresholds | [backend/migrations/versions/0004_invites_and_org_thresholds.py](backend/migrations/versions/0004_invites_and_org_thresholds.py) |
| `0005_job_state_lifecycle` | `0004_invites_and_org_thresholds` | Job state lifecycle | [backend/migrations/versions/0005_job_state_lifecycle.py](backend/migrations/versions/0005_job_state_lifecycle.py) |
| `0006_outbox_events` | `0005_job_state_lifecycle` | Outbox events | [backend/migrations/versions/0006_outbox_events.py](backend/migrations/versions/0006_outbox_events.py) |
| `0007_refresh_reuse_detection` | `0006_outbox_events` | Refresh reuse detection | [backend/migrations/versions/0007_refresh_reuse_detection.py](backend/migrations/versions/0007_refresh_reuse_detection.py) |
| `0008_alerts_open_partial_index` | `0007_refresh_reuse_detection` | Alerts open partial index | [backend/migrations/versions/0008_alerts_open_partial_index.py](backend/migrations/versions/0008_alerts_open_partial_index.py) |
| `0009_plans_usage_import_history` | `0008_alerts_open_partial_index` | Plans usage import history | [backend/migrations/versions/0009_plans_usage_import_history.py](backend/migrations/versions/0009_plans_usage_import_history.py) |
| `0010_confirm_and_billing` | `0009_plans_usage_import_history` | Confirm and billing | [backend/migrations/versions/0010_confirm_and_billing.py](backend/migrations/versions/0010_confirm_and_billing.py) |
| `0011_ops_billing` | `0010_confirm_and_billing` | Notifications billing and scheduler | [backend/migrations/versions/0011_notifications_billing_and_scheduler.py](backend/migrations/versions/0011_notifications_billing_and_scheduler.py) |
| `0012_import_profiles` | `0011_ops_billing` | Import mapping profiles | [backend/migrations/versions/0012_import_mapping_profiles.py](backend/migrations/versions/0012_import_mapping_profiles.py) |
| `0013_tx_search_trgm` | `0012_import_profiles` | Tx search trgm indexes | [backend/migrations/versions/0013_tx_search_trgm_indexes.py](backend/migrations/versions/0013_tx_search_trgm_indexes.py) |
| `0014_alert_assignment` | `0013_tx_search_trgm` | Alert assignment workflow | [backend/migrations/versions/0014_alert_assignment_workflow.py](backend/migrations/versions/0014_alert_assignment_workflow.py) |
| `0015_mfa_sessions` | `0014_alert_assignment` | Mfa and session management | [backend/migrations/versions/0015_mfa_and_session_management.py](backend/migrations/versions/0015_mfa_and_session_management.py) |
| `0016_mfa_recovery_codes` | `0015_mfa_sessions` | Mfa recovery codes | [backend/migrations/versions/0016_mfa_recovery_codes.py](backend/migrations/versions/0016_mfa_recovery_codes.py) |
| `0017_idempotency_keys` | `0016_mfa_recovery_codes` | Idempotency keys | [backend/migrations/versions/0017_idempotency_keys.py](backend/migrations/versions/0017_idempotency_keys.py) |
| `0018_owner_security_policy` | `0017_idempotency_keys` | Owner security policy | [backend/migrations/versions/0018_owner_security_policy.py](backend/migrations/versions/0018_owner_security_policy.py) |
| `0019_privacy_and_deletion_baseline` | `0018_owner_security_policy` | Privacy and deletion baseline | [backend/migrations/versions/0019_privacy_and_deletion_baseline.py](backend/migrations/versions/0019_privacy_and_deletion_baseline.py) |
| `0020_dead_letter_events` | `0019_privacy_and_deletion_baseline` | Dead letter events | [backend/migrations/versions/0020_dead_letter_events.py](backend/migrations/versions/0020_dead_letter_events.py) |
| `0021_bank_integrations_plaid_foundation` | `0020_dead_letter_events` | Bank integrations plaid foundation | [backend/migrations/versions/0021_bank_integrations_plaid_foundation.py](backend/migrations/versions/0021_bank_integrations_plaid_foundation.py) |
| `0022_payment_integrations_stripe_foundation` | `0021_bank_integrations_plaid_foundation` | Payment integrations stripe foundation | [backend/migrations/versions/0022_payment_integrations_stripe_foundation.py](backend/migrations/versions/0022_payment_integrations_stripe_foundation.py) |
| `0023_budgets_foundation` | `0022_payment_integrations_stripe_foundation` | Budgets foundation | [backend/migrations/versions/0023_budgets_foundation.py](backend/migrations/versions/0023_budgets_foundation.py) |
| `0024_org_budget_threshold_setting` | `0023_budgets_foundation` | Org budget threshold setting | [backend/migrations/versions/0024_org_budget_threshold_setting.py](backend/migrations/versions/0024_org_budget_threshold_setting.py) |
| `0025_locations_dimension` | `0024_org_budget_threshold_setting` | Locations dimension | [backend/migrations/versions/0025_locations_dimension.py](backend/migrations/versions/0025_locations_dimension.py) |
| `0026_alerts_location_scope` | `0025_locations_dimension` | Alerts location scope | [backend/migrations/versions/0026_alerts_location_scope.py](backend/migrations/versions/0026_alerts_location_scope.py) |
| `0027_inventory_forecasting_foundation` | `0026_alerts_location_scope` | Inventory forecasting foundation | [backend/migrations/versions/0027_inventory_forecasting_foundation.py](backend/migrations/versions/0027_inventory_forecasting_foundation.py) |
| `0028_ai_chat_assistant_foundation` | `0027_inventory_forecasting_foundation` | Ai chat assistant foundation | [backend/migrations/versions/0028_ai_chat_assistant_foundation.py](backend/migrations/versions/0028_ai_chat_assistant_foundation.py) |
| `0029_workforce_phase1_foundation` | `0028_ai_chat_assistant_foundation` | Workforce phase1 foundation | [backend/migrations/versions/0029_workforce_phase1_foundation.py](backend/migrations/versions/0029_workforce_phase1_foundation.py) |
| `0030_workforce_attendance_and_shifts` | `0029_workforce_phase1_foundation` | Workforce attendance and shifts | [backend/migrations/versions/0030_workforce_attendance_and_shifts.py](backend/migrations/versions/0030_workforce_attendance_and_shifts.py) |
| `0031_workforce_leave` | `0030_workforce_attendance_and_shifts` | Workforce leave | [backend/migrations/versions/0031_workforce_leave.py](backend/migrations/versions/0031_workforce_leave.py) |
| `0032_workforce_payroll` | `0031_workforce_leave` | Workforce payroll | [backend/migrations/versions/0032_workforce_payroll.py](backend/migrations/versions/0032_workforce_payroll.py) |
| `0033_workforce_payroll_unpaid_leave_deduction` | `0032_workforce_payroll` | Workforce payroll unpaid leave deduction | [backend/migrations/versions/0033_workforce_payroll_unpaid_leave_deduction.py](backend/migrations/versions/0033_workforce_payroll_unpaid_leave_deduction.py) |
| `0034_workforce_announcements` | `0033_workforce_payroll_unpaid_leave_deduction` | Workforce announcements | [backend/migrations/versions/0034_workforce_announcements.py](backend/migrations/versions/0034_workforce_announcements.py) |
| `0035_workforce_announcements_phase5` | `0034_workforce_announcements` | Workforce announcements phase5 | [backend/migrations/versions/0035_workforce_announcements_phase5.py](backend/migrations/versions/0035_workforce_announcements_phase5.py) |
| `0036_workforce_announcement_automation_dedupe` | `0035_workforce_announcements_phase5` | Workforce announcement automation dedupe | [backend/migrations/versions/0036_workforce_announcement_automation_dedupe.py](backend/migrations/versions/0036_workforce_announcement_automation_dedupe.py) |
| `0037_workforce_hr_admin_phase6` | `0036_workforce_announcement_automation_dedupe` | Workforce hr admin phase6 | [backend/migrations/versions/0037_workforce_hr_admin_phase6.py](backend/migrations/versions/0037_workforce_hr_admin_phase6.py) |
| `0038_workforce_policy_ack_updated_at_default` | `0037_workforce_hr_admin_phase6` | Workforce policy ack updated at default | [backend/migrations/versions/0038_workforce_policy_ack_updated_at_default.py](backend/migrations/versions/0038_workforce_policy_ack_updated_at_default.py) |
| `0039_org_settings_workforce_canonical_flag` | `0038_workforce_policy_ack_updated_at_default` | Org settings workforce canonical flag | [backend/migrations/versions/0039_org_settings_workforce_canonical_flag.py](backend/migrations/versions/0039_org_settings_workforce_canonical_flag.py) |
| `0040_auth_confirmation_code_and_provider_settings` | `0039_org_settings_workforce_canonical_flag` | Auth confirmation code and provider settings | [backend/migrations/versions/0040_auth_confirmation_code_and_provider_settings.py](backend/migrations/versions/0040_auth_confirmation_code_and_provider_settings.py) |

### G. Test inventory

Declared names are inventory, not fresh test passes. Parametrization adds cases and runtime opt-ins control skips.

- [backend/app/tests/conftest.py](backend/app/tests/conftest.py) — Shared fixtures/setup/helpers.

- [backend/app/tests/test_admin_operations.py](backend/app/tests/test_admin_operations.py) — `test_admin_outbox_endpoint`, `test_admin_system_status_endpoint`, `test_admin_outbox_retry_endpoint`, `test_admin_runtime_metrics_endpoint`, `test_admin_runtime_slos_endpoint`, `test_admin_audit_export_endpoint`, `test_admin_rotate_org_pii_endpoint`, `test_admin_deletion_requests_endpoint`, `test_admin_dead_letter_list_endpoint`, `test_admin_dead_letter_replay_endpoint`, `test_admin_dead_letter_dismiss_endpoint`

- [backend/app/tests/test_admin_recompute.py](backend/app/tests/test_admin_recompute.py) — `test_admin_recompute_enqueues_all_jobs`, `test_admin_recompute_forbidden_if_not_owner`, `test_admin_recompute_tenant_isolation`, `test_admin_recompute_forbidden_when_org_context_fails`

- [backend/app/tests/test_ai_chat_endpoint.py](backend/app/tests/test_ai_chat_endpoint.py) — `test_ai_chat_create_session`, `test_ai_chat_list_sessions`, `test_ai_chat_get_session`, `test_ai_chat_get_session_not_found`, `test_ai_chat_send_message`, `test_ai_health_endpoint_reports_provider_and_fallback`, `test_ai_health_endpoint_marks_fallback_unavailable`

- [backend/app/tests/test_ai_chat_service.py](backend/app/tests/test_ai_chat_service.py) — `test_ai_chat_service_roundtrip`, `test_ai_chat_service_not_found`, `test_ai_chat_service_list_sessions`

- [backend/app/tests/test_ai_grounding_validator.py](backend/app/tests/test_ai_grounding_validator.py) — `test_grounding_validator_accepts_grounded_response`, `test_grounding_validator_rejects_unsupported_metric`, `test_grounding_validator_rejects_mismatched_number`, `test_grounding_validator_rejects_unsupported_causal_sentence`, `test_grounding_validator_accepts_workforce_numbers_when_payload_present`, `test_grounding_validator_rejects_mismatched_time_window`

- [backend/app/tests/test_ai_service.py](backend/app/tests/test_ai_service.py) — `test_generate_summary_openai_success`, `test_generate_summary_ollama_server_success`, `test_generate_summary_ollama_server_relaxed_parsing`, `test_generate_summary_ollama_server_repair_retry`, `test_ai_provider_health_ollama_server_config_missing`, `test_ai_provider_health_ollama_server_live_check`, `test_ai_service_falls_back_on_provider_error`, `test_ai_service_falls_back_on_grounding_violation`, `test_ai_chat_uses_grounded_summary`, `test_ai_chat_falls_back_on_grounding_violation`

- [backend/app/tests/test_alembic_version_table_compat.py](backend/app/tests/test_alembic_version_table_compat.py) — `test_migration_revision_ids_fit_alembic_version_column`, `test_env_hardens_alembic_version_column_length`

- [backend/app/tests/test_alert_assignment_api.py](backend/app/tests/test_alert_assignment_api.py) — `test_assign_alert_rejects_non_member_assignee`, `test_acknowledge_alert_sets_acknowledged_timestamp`, `test_alert_history_returns_assignment_events`, `test_assign_alert_accepts_legacy_query_payload`, `test_acknowledge_alert_accepts_legacy_query_payload`, `test_assign_alert_accepts_partial_body_with_query_org`, `test_acknowledge_alert_accepts_empty_body_with_query_org`, `test_assign_alert_rejects_invalid_assignee_uuid`

- [backend/app/tests/test_alert_assignment_service.py](backend/app/tests/test_alert_assignment_service.py) — `test_assign_sets_assignment_and_clears_acknowledged_at`, `test_acknowledge_sets_timestamp`

- [backend/app/tests/test_alerts_anomaly_math.py](backend/app/tests/test_alerts_anomaly_math.py) — `test_mad_score_detects_spike`, `test_z_score_detects_spike_when_variance_exists`

- [backend/app/tests/test_alerts_budget_threshold.py](backend/app/tests/test_alerts_budget_threshold.py) — `test_detect_budget_threshold_creates_persistent_alert_with_audit_metadata`, `test_detect_budget_threshold_ignores_rows_below_threshold`

- [backend/app/tests/test_alerts_inventory_stockout.py](backend/app/tests/test_alerts_inventory_stockout.py) — `test_inventory_stockout_detection_creates_high_risk_alert`

- [backend/app/tests/test_alerts_location_filter.py](backend/app/tests/test_alerts_location_filter.py) — `test_list_alerts_passes_location_filter`

- [backend/app/tests/test_alerts_location_scoping.py](backend/app/tests/test_alerts_location_scoping.py) — `test_detect_and_create_runs_global_and_location_contexts`

- [backend/app/tests/test_alerts_ordering.py](backend/app/tests/test_alerts_ordering.py) — `test_alerts_are_ranked_by_severity_then_impact_then_recency`

- [backend/app/tests/test_alerts_refresh_service.py](backend/app/tests/test_alerts_refresh_service.py) — `test_enqueue_recalc_reuses_existing_active_job`, `test_enqueue_recalc_dispatches_and_tracks_job`

- [backend/app/tests/test_analytics.py](backend/app/tests/test_analytics.py) — `test_summary_calc`

- [backend/app/tests/test_analytics_budget_variance_endpoint.py](backend/app/tests/test_analytics_budget_variance_endpoint.py) — `test_budget_variance_endpoint`

- [backend/app/tests/test_analytics_location_benchmark_endpoint.py](backend/app/tests/test_analytics_location_benchmark_endpoint.py) — `test_location_benchmark_endpoint_returns_grouped_metrics`, `test_location_benchmark_rejects_invalid_range`

- [backend/app/tests/test_analytics_recompute_endpoint.py](backend/app/tests/test_analytics_recompute_endpoint.py) — `test_analytics_recompute_enqueues_single_job`, `test_analytics_recompute_reuses_active_job`, `test_analytics_recompute_replays_idempotent_response`

- [backend/app/tests/test_api_integration_live.py](backend/app/tests/test_api_integration_live.py) — `test_live_acceptance_flow`

- [backend/app/tests/test_auth.py](backend/app/tests/test_auth.py) — `test_refresh_hashing_stable`, `test_refresh_rotation_semantics`

- [backend/app/tests/test_auth_cookie_integration_live.py](backend/app/tests/test_auth_cookie_integration_live.py) — `test_cookie_auth_login_refresh_logout_flow`

- [backend/app/tests/test_auth_delete_account_endpoint.py](backend/app/tests/test_auth_delete_account_endpoint.py) — `test_delete_account_creates_request`, `test_list_delete_account_requests`

- [backend/app/tests/test_auth_dev_confirmation_endpoint.py](backend/app/tests/test_auth_dev_confirmation_endpoint.py) — `test_dev_confirmation_token_returns_latest_token`, `test_dev_confirmation_token_hidden_outside_development`

- [backend/app/tests/test_auth_lockout_endpoint.py](backend/app/tests/test_auth_lockout_endpoint.py) — `test_login_rejects_when_lockout_is_active`, `test_login_records_failure_and_returns_unauthorized`

- [backend/app/tests/test_auth_lockout_metrics.py](backend/app/tests/test_auth_lockout_metrics.py) — `test_record_login_failure_tracks_escalation_metrics`, `test_clear_login_failures_clears_escalation_key`

- [backend/app/tests/test_auth_mfa_service.py](backend/app/tests/test_auth_mfa_service.py) — `test_login_requires_mfa_code_when_enabled`, `test_login_succeeds_with_valid_mfa_code`, `test_login_succeeds_with_valid_recovery_code_and_consumes_it`

- [backend/app/tests/test_auth_mfa_session_endpoints.py](backend/app/tests/test_auth_mfa_session_endpoints.py) — `test_mfa_enable_and_regenerate_return_recovery_codes`, `test_login_passes_mfa_recovery_code_to_service`, `test_sessions_endpoint_forwards_refresh_token_to_service`, `test_reauth_returns_token`

- [backend/app/tests/test_auth_owner_mfa_policy.py](backend/app/tests/test_auth_owner_mfa_policy.py) — `test_login_blocks_owner_without_mfa_when_policy_requires_it`

- [backend/app/tests/test_auth_refresh_reuse.py](backend/app/tests/test_auth_refresh_reuse.py) — `test_refresh_rotation_still_works`, `test_refresh_reuse_triggers_session_revocation`

- [backend/app/tests/test_auth_registration_confirmation.py](backend/app/tests/test_auth_registration_confirmation.py) — `test_register_creates_inactive_user_and_confirmation_outbox_event`, `test_confirm_registration_activates_user_and_marks_token_used`, `test_confirm_registration_rejects_invalid_token`, `test_resend_confirmation_creates_new_outbox_event_for_inactive_user`

- [backend/app/tests/test_auth_session_management_service.py](backend/app/tests/test_auth_session_management_service.py) — `test_list_sessions_marks_current`, `test_revoke_other_sessions_keeps_current`

- [backend/app/tests/test_auth_session_tokens.py](backend/app/tests/test_auth_session_tokens.py) — `test_issue_registration_tokens_creates_session_and_tokens`, `test_refresh_rejects_inactive_account_and_revokes_session`

- [backend/app/tests/test_bank_provider.py](backend/app/tests/test_bank_provider.py) — `test_stub_bank_provider_link_exchange_and_sync`

- [backend/app/tests/test_banks_tasks.py](backend/app/tests/test_banks_tasks.py) — `test_sync_all_active_enqueues_connections_with_actor`

- [backend/app/tests/test_budget_service.py](backend/app/tests/test_budget_service.py) — `test_create_budget_versions_replace_current`, `test_budget_variance_includes_unbudgeted_actual_category`, `test_budget_variance_all_mode_separates_actuals_by_type`

- [backend/app/tests/test_budgets_endpoint.py](backend/app/tests/test_budgets_endpoint.py) — `test_budget_create_list_update_flow`, `test_budget_mutations_forbidden_for_viewer`

- [backend/app/tests/test_bulk_remap_recompute.py](backend/app/tests/test_bulk_remap_recompute.py) — `test_bulk_remap_recomputes_all_touched_months`

- [backend/app/tests/test_celery_task_registration.py](backend/app/tests/test_celery_task_registration.py) — `test_celery_registers_alerts_forecasts_outbox_tasks`

- [backend/app/tests/test_csv_import.py](backend/app/tests/test_csv_import.py) — `test_csv_preview_parse`, `test_csv_type_alias_income_and_cost_supported`, `test_csv_missing_required_mapped_column_raises`, `test_csv_optional_location_mapping_is_supported`

- [backend/app/tests/test_csv_import_duplicates.py](backend/app/tests/test_csv_import_duplicates.py) — `test_csv_import_skips_duplicates`, `test_csv_import_resolves_location_mapping`, `test_csv_import_fails_for_unknown_location`

- [backend/app/tests/test_db_session_pool_config.py](backend/app/tests/test_db_session_pool_config.py) — `test_db_engine_uses_configured_pool_settings`, `test_db_engine_uses_worker_pool_overrides`

- [backend/app/tests/test_dead_letter_model.py](backend/app/tests/test_dead_letter_model.py) — `test_dead_letter_event_has_updated_at_column`

- [backend/app/tests/test_error_envelope.py](backend/app/tests/test_error_envelope.py) — `test_http_error_uses_standard_envelope`, `test_validation_error_uses_standard_envelope`

- [backend/app/tests/test_events_endpoint.py](backend/app/tests/test_events_endpoint.py) — `test_events_stream_returns_sse_response`

- [backend/app/tests/test_health_endpoint.py](backend/app/tests/test_health_endpoint.py) — `test_health_reports_auth_cookie_mode`

- [backend/app/tests/test_https_enforcement.py](backend/app/tests/test_https_enforcement.py) — `test_https_enforcement_blocks_plain_http`, `test_https_enforcement_allows_forwarded_https`

- [backend/app/tests/test_idempotency_service.py](backend/app/tests/test_idempotency_service.py) — `test_get_replay_returns_existing_response`, `test_get_replay_rejects_mismatched_payload`, `test_store_response_noops_without_key`, `test_store_response_persists_with_ttl`

- [backend/app/tests/test_import_mapping_profile_model.py](backend/app/tests/test_import_mapping_profile_model.py) — `test_import_mapping_profile_includes_updated_at_column`

- [backend/app/tests/test_import_profiles_endpoint.py](backend/app/tests/test_import_profiles_endpoint.py) — `test_import_profile_crud_and_list`, `test_import_profile_mutation_forbidden_for_viewer`, `test_import_csv_uses_saved_profile_mapping`, `test_import_csv_profile_tenant_isolation`, `test_import_csv_preview_does_not_enqueue_alert_recalc`

- [backend/app/tests/test_integrations_endpoint.py](backend/app/tests/test_integrations_endpoint.py) — `test_link_token_endpoint`, `test_exchange_endpoint`, `test_sync_enqueue_endpoint`, `test_stripe_connect_endpoint`, `test_list_payment_connections_endpoint`, `test_payment_reconciliation_endpoint`

- [backend/app/tests/test_integrations_payments_webhook.py](backend/app/tests/test_integrations_payments_webhook.py) — `test_stripe_webhook_success`, `test_stripe_webhook_bad_payload_returns_400`

- [backend/app/tests/test_integrations_webhook.py](backend/app/tests/test_integrations_webhook.py) — `test_plaid_webhook_rejects_invalid_signature`, `test_plaid_webhook_enqueues_sync`

- [backend/app/tests/test_inventory_endpoint.py](backend/app/tests/test_inventory_endpoint.py) — `test_inventory_list_and_forecast`, `test_inventory_mutations_forbidden_for_viewer`, `test_inventory_create_item_sets_alert_refresh_headers`

- [backend/app/tests/test_inventory_repo_duplicate_tolerance.py](backend/app/tests/test_inventory_repo_duplicate_tolerance.py) — `test_get_stock_level_tolerates_duplicate_rows`, `test_upsert_sales_velocity_tolerates_duplicate_rows`

- [backend/app/tests/test_inventory_service.py](backend/app/tests/test_inventory_service.py) — `test_create_item_normalizes_and_rejects_duplicates`, `test_record_stock_event_updates_stock_level`, `test_forecast_marks_high_risk_when_cover_is_short`

- [backend/app/tests/test_job_repo_race.py](backend/app/tests/test_job_repo_race.py) — `test_upsert_running_handles_concurrent_insert_race_without_task_id_drift`, `test_upsert_pending_does_not_downgrade_running_row_after_race`

- [backend/app/tests/test_jobs_commands.py](backend/app/tests/test_jobs_commands.py) — `test_jobs_retry_endpoint`, `test_jobs_cancel_endpoint`

- [backend/app/tests/test_jobs_endpoint.py](backend/app/tests/test_jobs_endpoint.py) — `test_jobs_endpoint_viewer_redacts_sensitive_fields`, `test_jobs_endpoint_uses_context_org_for_tenant_scoping`, `test_jobs_endpoint_forbidden_when_org_context_fails`

- [backend/app/tests/test_location_service.py](backend/app/tests/test_location_service.py) — `test_create_location_rejects_duplicate`, `test_ensure_org_location_rejects_inactive`, `test_update_location_not_found`

- [backend/app/tests/test_locations_endpoint.py](backend/app/tests/test_locations_endpoint.py) — `test_list_locations_returns_payload`, `test_create_location_forbidden_for_viewer`

- [backend/app/tests/test_mfa_utils.py](backend/app/tests/test_mfa_utils.py) — `test_encrypt_and_decrypt_round_trip`, `test_verify_totp_code_accepts_current_window`, `test_verify_totp_code_rejects_invalid_code`

- [backend/app/tests/test_notifications_endpoint.py](backend/app/tests/test_notifications_endpoint.py) — `test_notifications_list_and_mark_read`, `test_notifications_mark_all`

- [backend/app/tests/test_org_billing_endpoint.py](backend/app/tests/test_org_billing_endpoint.py) — `test_billing_get_and_put_owner_only_success`, `test_billing_editor_forbidden`, `test_org_delete_request_owner`

- [backend/app/tests/test_org_security_policy_endpoint.py](backend/app/tests/test_org_security_policy_endpoint.py) — `test_update_settings_blocks_editor_from_security_fields`, `test_update_settings_allows_editor_financial_fields`

- [backend/app/tests/test_org_settings_validation.py](backend/app/tests/test_org_settings_validation.py) — `test_org_settings_validation_rejects_invalid_ranges`

- [backend/app/tests/test_organizations_invite_visibility.py](backend/app/tests/test_organizations_invite_visibility.py) — `test_invite_hides_token_when_exposure_disabled`, `test_invite_returns_token_when_exposure_enabled`

- [backend/app/tests/test_outbox.py](backend/app/tests/test_outbox.py) — `test_report_generation_enqueues_outbox_event`, `test_outbox_consumer_sends_and_marks_delivered`, `test_outbox_consumer_retries_then_fails`, `test_outbox_consumer_marks_dry_run_email`

- [backend/app/tests/test_outbox_dead_letter.py](backend/app/tests/test_outbox_dead_letter.py) — `test_outbox_terminal_failure_records_dead_letter`

- [backend/app/tests/test_owner_policy_deps.py](backend/app/tests/test_owner_policy_deps.py) — `test_get_org_context_blocks_owner_when_mfa_required`, `test_get_org_context_blocks_expired_owner_session`, `test_require_sensitive_reauth_blocks_without_reauth_token`, `test_require_sensitive_reauth_accepts_valid_reauth_token`

- [backend/app/tests/test_payment_integration_service.py](backend/app/tests/test_payment_integration_service.py) — `test_ingest_duplicate_event_returns_duplicate`, `test_ingest_charge_succeeded_records_ledger`, `test_ingest_unsupported_event_skips`, `test_reconcile_computes_delta`

- [backend/app/tests/test_period_month_query.py](backend/app/tests/test_period_month_query.py) — `test_parse_period_month_yyyy_mm`, `test_parse_period_month_yyyy_mm_dd`, `test_parse_period_month_none`, `test_parse_period_month_invalid`

- [backend/app/tests/test_pii_crypto.py](backend/app/tests/test_pii_crypto.py) — `test_encrypt_decrypt_roundtrip`, `test_hash_is_stable`

- [backend/app/tests/test_plaid_sandbox_live.py](backend/app/tests/test_plaid_sandbox_live.py) — `test_live_plaid_sandbox_integration_flow`

- [backend/app/tests/test_plan_repo_usage_race.py](backend/app/tests/test_plan_repo_usage_race.py) — `test_ensure_usage_handles_concurrent_insert_race`

- [backend/app/tests/test_plan_usage_endpoint.py](backend/app/tests/test_plan_usage_endpoint.py) — `test_plan_usage_endpoint`

- [backend/app/tests/test_rbac.py](backend/app/tests/test_rbac.py) — `test_viewer_cannot_edit`, `test_owner_can_invite`

- [backend/app/tests/test_read_caching_endpoints.py](backend/app/tests/test_read_caching_endpoints.py) — `test_alerts_list_uses_short_ttl_cache`, `test_transactions_list_uses_short_ttl_cache`, `test_analytics_summary_uses_short_ttl_cache`

- [backend/app/tests/test_report_service_roundtrip.py](backend/app/tests/test_report_service_roundtrip.py) — `test_report_generate_and_download_roundtrip`, `test_report_download_url_uses_public_minio_base`

- [backend/app/tests/test_reports_endpoint.py](backend/app/tests/test_reports_endpoint.py) — `test_generate_report_enqueues_async_job`, `test_generate_report_returns_active_job_when_already_running`, `test_generate_report_reuses_existing_report`, `test_generate_report_replays_from_idempotency_store`, `test_generate_report_location_scope_changes_dedupe_key`

- [backend/app/tests/test_reports_idempotent.py](backend/app/tests/test_reports_idempotent.py) — `test_report_key_stable`

- [backend/app/tests/test_reports_task.py](backend/app/tests/test_reports_task.py) — `test_generate_worker_runner_persists_report`

- [backend/app/tests/test_runway.py](backend/app/tests/test_runway.py) — `test_runway_conservative`

- [backend/app/tests/test_security_tokens.py](backend/app/tests/test_security_tokens.py) — `test_create_token_has_unique_jti_per_mint`

- [backend/app/tests/test_slo_metrics.py](backend/app/tests/test_slo_metrics.py) — `test_runtime_slo_snapshot_calculates_p95_and_error_rate`

- [backend/app/tests/test_stripe_sandbox_live.py](backend/app/tests/test_stripe_sandbox_live.py) — `test_live_stripe_sandbox_webhook_flow`

- [backend/app/tests/test_task_tracking.py](backend/app/tests/test_task_tracking.py) — `test_run_tracked_task_success`, `test_run_tracked_task_retrying`, `test_run_tracked_task_failed_after_max_retries`

- [backend/app/tests/test_tenant_isolation.py](backend/app/tests/test_tenant_isolation.py) — `test_cross_org_requests_are_rejected`

- [backend/app/tests/test_transaction_import_history_endpoint.py](backend/app/tests/test_transaction_import_history_endpoint.py) — `test_import_history_list_and_error_download`

- [backend/app/tests/test_transactions.py](backend/app/tests/test_transactions.py) — `test_transaction_schema_accepts_decimal`

- [backend/app/tests/test_transactions_alert_refresh_enqueue.py](backend/app/tests/test_transactions_alert_refresh_enqueue.py) — `test_transaction_mutations_enqueue_alert_recalc`, `test_transaction_create_idempotent_replay_skips_enqueue`, `test_bulk_remap_zero_updates_does_not_enqueue`

- [backend/app/tests/test_transactions_jobs_alert_enqueue_integration.py](backend/app/tests/test_transactions_jobs_alert_enqueue_integration.py) — `test_transaction_create_enqueues_alert_job_visible_in_jobs_endpoint`

- [backend/app/tests/test_usage_limits.py](backend/app/tests/test_usage_limits.py) — `test_usage_limit_exceeded`, `test_usage_overview_returns_metrics`

- [backend/app/tests/test_workforce_announcement_automation.py](backend/app/tests/test_workforce_announcement_automation.py) — `test_automation_keys_registry_nonempty_and_sorted_convention`, `test_render_template_text_substitutes`, `test_render_template_text_unknown_placeholder_preserved`, `test_render_template_text_multiple_keys`

- [backend/app/tests/test_workforce_announcement_service.py](backend/app/tests/test_workforce_announcement_service.py) — `test_visible_org_all_without_employee`, `test_department_audience_requires_employee_match`, `test_department_audience_visible_when_department_matches`, `test_manager_team_visible_when_manager_matches`, `test_validate_audience_targeted_requires_ids`

- [backend/app/tests/test_workforce_attendance_endpoints.py](backend/app/tests/test_workforce_attendance_endpoints.py) — `test_clock_in_forbidden_for_viewer`, `test_clock_out_requires_clock_in`, `test_daily_view_returns_items`, `test_calendar_rejects_invalid_month`, `test_correction_request_forbidden_for_viewer`, `test_correction_review_404`

- [backend/app/tests/test_workforce_frontend_contracts.py](backend/app/tests/test_workforce_frontend_contracts.py) — `test_workforce_payroll_downloads_do_not_send_org_id_query`, `test_workforce_hooks_canonical_routes_do_not_build_org_id_queries`, `test_workforce_hooks_do_not_send_org_id_in_mutation_payloads`

- [backend/app/tests/test_workforce_leave_endpoints.py](backend/app/tests/test_workforce_leave_endpoints.py) — `test_leave_type_create_forbidden_for_viewer`, `test_leave_types_list_ok`, `test_leave_request_decision_404`, `test_leave_request_create_422`

- [backend/app/tests/test_workforce_leave_overlap.py](backend/app/tests/test_workforce_leave_overlap.py) — `test_overlap_inclusive_calendar_days_full_overlap`, `test_overlap_inclusive_calendar_days_no_overlap`

- [backend/app/tests/test_workforce_leave_service.py](backend/app/tests/test_workforce_leave_service.py) — `test_cancelled_leave_reverts_leave_attendance_row`

- [backend/app/tests/test_workforce_notifications.py](backend/app/tests/test_workforce_notifications.py) — `test_leave_decision_emits_notification`, `test_payroll_mark_paid_emits_notification`, `test_hr_checklist_done_emits_notification`

- [backend/app/tests/test_workforce_org_context_canonical.py](backend/app/tests/test_workforce_org_context_canonical.py) — `test_workforce_org_context_allows_fallback_when_flag_disabled`, `test_workforce_org_context_requires_header_when_flag_enabled`, `test_workforce_org_context_accepts_matching_header_when_flag_enabled`

- [backend/app/tests/test_workforce_payroll_endpoints.py](backend/app/tests/test_workforce_payroll_endpoints.py) — `test_payroll_create_period_forbidden_for_viewer`, `test_payroll_create_adjustment_forbidden_for_viewer`, `test_payroll_list_entries_redacts_for_viewer`, `test_payroll_list_entries_shows_amounts_for_editor`, `test_payroll_mark_paid_forbidden_for_editor`, `test_payroll_mark_paid_ok_for_owner`, `test_payroll_payslip_pdf_returns_pdf_bytes`, `test_payroll_payslip_pdf_allowed_for_viewer`

- [backend/app/tests/test_workforce_payroll_service.py](backend/app/tests/test_workforce_payroll_service.py) — `test_hourly_overtime_gross_pay`, `test_salaried_gross_pay_ignores_hours`, `test_salaried_gross_subtracts_unpaid_leave_snapshot`, `test_adjustments_affect_net_pay`, `test_blank_salary_type_defaults_to_salaried`, `test_unknown_salary_type_zero_gross`

- [backend/app/tests/test_workforce_payslip_pdf.py](backend/app/tests/test_workforce_payslip_pdf.py) — `test_payslip_pdf_is_valid_pdf`

- [backend/app/tests/test_workforce_phase1_endpoints.py](backend/app/tests/test_workforce_phase1_endpoints.py) — `test_employee_list_redacts_salary_for_viewer`, `test_employee_create_forbidden_for_viewer`, `test_employee_create_forbidden_for_manager`, `test_department_create_allowed_for_editor`, `test_workforce_endpoints_reject_cross_org`, `test_workforce_endpoints_reject_header_query_org_mismatch`, `test_workforce_endpoints_reject_header_body_org_mismatch`, `test_employee_list_filters_for_manager_scope`

- [backend/app/tests/test_workforce_phase6_hr_endpoints.py](backend/app/tests/test_workforce_phase6_hr_endpoints.py) — `test_hr_policy_create_forbidden_for_viewer`, `test_hr_checklist_create_forbidden_for_viewer`

- [backend/app/tests/test_workforce_phase7_intelligence_endpoint.py](backend/app/tests/test_workforce_phase7_intelligence_endpoint.py) — `test_workforce_intelligence_dashboard_smoke`, `test_workforce_intelligence_reports_summary_smoke`

- [frontend/e2e/ai-chat.spec.ts](frontend/e2e/ai-chat.spec.ts) — AI chat flow: create session, send message, and show grounded/fallback indicator

- [frontend/e2e/alert-refresh-queue.spec.ts](frontend/e2e/alert-refresh-queue.spec.ts) — transaction mutation emits alert refresh queue signal and yields persisted budget-threshold alert

- [frontend/e2e/alerts-actions.spec.ts](frontend/e2e/alerts-actions.spec.ts) — alerts actions: open feed allows dismiss (owner/editor)

- [frontend/e2e/auth-confirm-ui.spec.ts](frontend/e2e/auth-confirm-ui.spec.ts) — shows activation form and surfaces error for bogus token; happy path: register → dev token → confirm UI → login

- [frontend/e2e/budgets.spec.ts](frontend/e2e/budgets.spec.ts) — budgets flow: create and version update

- [frontend/e2e/cookie-csrf.spec.ts](frontend/e2e/cookie-csrf.spec.ts) — blocks mutating request without CSRF and allows with CSRF

- [frontend/e2e/dashboard-budget-variance.spec.ts](frontend/e2e/dashboard-budget-variance.spec.ts) — dashboard shows budget variance KPIs and threshold alerts

- [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts) — Global setup/authentication fixtures and browser-test helpers.

- [frontend/e2e/full-flow.spec.ts](frontend/e2e/full-flow.spec.ts) — full app flow: auth fixture -> dashboard -> transactions -> reports

- [frontend/e2e/global-setup.ts](frontend/e2e/global-setup.ts) — Global setup/authentication fixtures and browser-test helpers.

- [frontend/e2e/imports-workflow.spec.ts](frontend/e2e/imports-workflow.spec.ts) — imports workflow: upload → map → preview → commit → import history updates

- [frontend/e2e/inventory-alerts.spec.ts](frontend/e2e/inventory-alerts.spec.ts) — inventory flow: mutate stock, queue refresh, and surface persisted stockout alert

- [frontend/e2e/mfa-session.spec.ts](frontend/e2e/mfa-session.spec.ts) — mfa and session API smoke

- [frontend/e2e/onboarding-workspace.spec.ts](frontend/e2e/onboarding-workspace.spec.ts) — onboarding workspace loads after auth

- [frontend/e2e/ops-flow.spec.ts](frontend/e2e/ops-flow.spec.ts) — registration routes to confirmation page; confirmation page shows backend failure for invalid token; invite acceptance flow creates a usable account; operations and admin console surfaces handle role-aware tooling; settings page exposes deletion request controls; top-level protected aliases render without redirect-only route loss; login succeeds when return_to context is present

- [frontend/e2e/plaid-integration.spec.ts](frontend/e2e/plaid-integration.spec.ts) — connects bank via public token and enqueues sync

- [frontend/e2e/polish.spec.ts](frontend/e2e/polish.spec.ts) — transactions csv mapping required-field guard disables import actions; guided onboarding rail appears for a fresh organization; transactions bulk remap success path updates category and shows toast; forecast inline override supports dirty state, save and reset; rbac smoke: viewer-style UI does not expose add transaction action

- [frontend/e2e/rbac-viewer-api.spec.ts](frontend/e2e/rbac-viewer-api.spec.ts) — viewer bearer session cannot create transactions (403)

- [frontend/e2e/rbac-viewer-settings-api.spec.ts](frontend/e2e/rbac-viewer-settings-api.spec.ts) — viewer bearer session cannot mutate org settings or integrations (403)

- [frontend/e2e/reports-workflow.spec.ts](frontend/e2e/reports-workflow.spec.ts) — reports workflow: generate and surface recent jobs

- [frontend/e2e/responsive-mobile.spec.ts](frontend/e2e/responsive-mobile.spec.ts) — mobile shell: opens slide-out nav and navigates to Money

- [frontend/e2e/responsive-smoke.spec.ts](frontend/e2e/responsive-smoke.spec.ts) — dashboard loads and primary actions remain reachable

- [frontend/e2e/sse-fallback.spec.ts](frontend/e2e/sse-fallback.spec.ts) — SSE fallback activates and recovers to live

- [frontend/e2e/stripe-integration.spec.ts](frontend/e2e/stripe-integration.spec.ts) — connects Stripe and processes live signed webhook into reconciliation

- [frontend/e2e/stripe-reconciliation-invalid-range.spec.ts](frontend/e2e/stripe-reconciliation-invalid-range.spec.ts) — stripe reconciliation shows friendly invalid date range error

- [frontend/e2e/transactions-workflow.spec.ts](frontend/e2e/transactions-workflow.spec.ts) — transactions workflow: create → edit → bulk delete

- [frontend/e2e/visual.spec.ts](frontend/e2e/visual.spec.ts) — Global setup/authentication fixtures and browser-test helpers.

- [frontend/e2e/workforce-activity-failure-retry.spec.ts](frontend/e2e/workforce-activity-failure-retry.spec.ts) — outbox failed event renders and retry action posts successfully

- [frontend/e2e/workforce-attendance.spec.ts](frontend/e2e/workforce-attendance.spec.ts) — attendance page loads with tabs

- [frontend/e2e/workforce-communications-failure-states.spec.ts](frontend/e2e/workforce-communications-failure-states.spec.ts) — delivery log API supports failed/retrying filters and error fields

- [frontend/e2e/workforce-hr-admin.spec.ts](frontend/e2e/workforce-hr-admin.spec.ts) — policies + acknowledgements + checklists + documents upload

- [frontend/e2e/workforce-leave-workflow.spec.ts](frontend/e2e/workforce-leave-workflow.spec.ts) — allocate → request → approve → calendar shows leave

- [frontend/e2e/workforce-leave.spec.ts](frontend/e2e/workforce-leave.spec.ts) — leave page loads with tabs

- [frontend/e2e/workforce-mobile-dense-interactions.spec.ts](frontend/e2e/workforce-mobile-dense-interactions.spec.ts) — attendance and payroll controls stay usable on mobile width

- [frontend/e2e/workforce-onboarding-offboarding.spec.ts](frontend/e2e/workforce-onboarding-offboarding.spec.ts) — create and complete onboarding/offboarding checklist flows

- [frontend/e2e/workforce-payroll-workflow.spec.ts](frontend/e2e/workforce-payroll-workflow.spec.ts) — create period → generate → adjustment → export CSV → approve → PDF → mark paid (owner)

- [frontend/e2e/workforce-payroll.spec.ts](frontend/e2e/workforce-payroll.spec.ts) — payroll page loads with period picker

- [frontend/e2e/workforce-phase1.spec.ts](frontend/e2e/workforce-phase1.spec.ts) — create department + title + employee, then filter/search employee directory

- [frontend/e2e/workforce-phase7-intelligence.spec.ts](frontend/e2e/workforce-phase7-intelligence.spec.ts) — dashboard + reports summary return JSON for current org

- [frontend/e2e/workforce-rbac-negative.spec.ts](frontend/e2e/workforce-rbac-negative.spec.ts) — workforce RBAC negative: viewer cannot mutate and cross-org is blocked

- [frontend/e2e/workforce-responsive.spec.ts](frontend/e2e/workforce-responsive.spec.ts) — Global setup/authentication fixtures and browser-test helpers.

- [frontend/e2e/workforce-state-matrix.spec.ts](frontend/e2e/workforce-state-matrix.spec.ts) — route error states render when workforce API fails; viewer sees permission-limited states on mutate surfaces

### H. Complete file catalog

Every tracked file present is catalogued, including the staged environment variant and historical/generated artifacts. Secrets and artifact payloads are not copied. Git internals, ignored dependency folders and build caches are outside authored-source coverage.

#### (root) files

| File | Responsibility |
| --- | --- |
| [.env.cookie](.env.cookie) | Environment template/variant. Private values are deliberately omitted; this file may contain credentials. |
| [.env.example](.env.example) | Environment template/variant. Private values are deliberately omitted; this file may contain credentials. |
| [.gitignore](.gitignore) | Configuration/generated contract/support artifact: .gitignore. |
| [.pre-commit-config.yaml](.pre-commit-config.yaml) | Configuration/generated contract/support artifact: .pre-commit-config.yaml. |
| [Makefile](Makefile) | Quality/runtime/backup convenience commands; some Python paths assume Windows. |
| [README.md](README.md) | Comprehensive project description and current source reference (this document). |
| [ai-live-mode-report.json](ai-live-mode-report.json) | Configuration/generated contract/support artifact: ai-live-mode-report.json. |
| [docker-compose.yml](docker-compose.yml) | Seven-service stack; PostgreSQL health-gated dependencies, roles, ports and volumes. |

#### .github files

| File | Responsibility |
| --- | --- |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | GitHub Actions quality/gated browser-provider integration workflow. |
| [.github/workflows/perf.yml](.github/workflows/perf.yml) | GitHub Actions performance bootstrap/load/gate/artifact workflow. |

#### .vscode files

| File | Responsibility |
| --- | --- |
| [.vscode/settings.json](.vscode/settings.json) | Editor/workspace settings. |

#### backend files

| File | Responsibility |
| --- | --- |
| [backend/.tmp-run-uvicorn-8001.cmd](backend/.tmp-run-uvicorn-8001.cmd) | Tracked local runtime/debug helper or log/PID artifact; not application source. |
| [backend/.tmp-uvicorn-8000.pid](backend/.tmp-uvicorn-8000.pid) | Tracked local runtime/debug helper or log/PID artifact; not application source. |
| [backend/.tmp-uvicorn-8001.err.log](backend/.tmp-uvicorn-8001.err.log) | Tracked local runtime/debug helper or log/PID artifact; not application source. |
| [backend/.tmp-uvicorn-8001.out.log](backend/.tmp-uvicorn-8001.out.log) | Tracked local runtime/debug helper or log/PID artifact; not application source. |
| [backend/.tmp-uvicorn-8001.pid](backend/.tmp-uvicorn-8001.pid) | Tracked local runtime/debug helper or log/PID artifact; not application source. |
| [backend/Dockerfile](backend/Dockerfile) | Container build/entrypoint for backend. |
| [backend/README.md](backend/README.md) | AI COO Backend. Sections: Run locally; Architecture; Security defaults; Cash balance definition; Burn / runway definition; CSV import safety; Job lifecycle tracking; Outbox reliability; Refresh token reuse detection; Admin recompute endpoint; Billing placeholders (owner-only); Realtime updates and polling fallback; Plans and usage limits; Import history; Quality. Historical/current guidance or proposals; compare with source. |
| [backend/ai_coo_backend.egg-info/PKG-INFO](backend/ai_coo_backend.egg-info/PKG-INFO) | Generated Python installation/package metadata. |
| [backend/ai_coo_backend.egg-info/SOURCES.txt](backend/ai_coo_backend.egg-info/SOURCES.txt) | Generated Python installation/package metadata. |
| [backend/ai_coo_backend.egg-info/dependency_links.txt](backend/ai_coo_backend.egg-info/dependency_links.txt) | Generated Python installation/package metadata. |
| [backend/ai_coo_backend.egg-info/requires.txt](backend/ai_coo_backend.egg-info/requires.txt) | Generated Python installation/package metadata. |
| [backend/ai_coo_backend.egg-info/top_level.txt](backend/ai_coo_backend.egg-info/top_level.txt) | Generated Python installation/package metadata. |
| [backend/alembic.ini](backend/alembic.ini) | Configuration/generated contract/support artifact: alembic.ini. |
| [backend/app/__init__.py](backend/app/__init__.py) | Python backend/operational/runtime/load tool:   init  . |
| [backend/app/api/__init__.py](backend/app/api/__init__.py) | HTTP routes/dependencies/query parsing:   init  . |
| [backend/app/api/deps.py](backend/app/api/deps.py) | HTTP routes/dependencies/query parsing: deps. |
| [backend/app/api/period_month.py](backend/app/api/period_month.py) | HTTP routes/dependencies/query parsing: period month. |
| [backend/app/api/v1/__init__.py](backend/app/api/v1/__init__.py) | HTTP routes/dependencies/query parsing:   init  . |
| [backend/app/api/v1/admin.py](backend/app/api/v1/admin.py) | HTTP routes/dependencies/query parsing: admin. |
| [backend/app/api/v1/ai.py](backend/app/api/v1/ai.py) | HTTP routes/dependencies/query parsing: ai. |
| [backend/app/api/v1/alerts.py](backend/app/api/v1/alerts.py) | HTTP routes/dependencies/query parsing: alerts. |
| [backend/app/api/v1/analytics.py](backend/app/api/v1/analytics.py) | HTTP routes/dependencies/query parsing: analytics. |
| [backend/app/api/v1/auth.py](backend/app/api/v1/auth.py) | HTTP routes/dependencies/query parsing: auth. |
| [backend/app/api/v1/budgets.py](backend/app/api/v1/budgets.py) | HTTP routes/dependencies/query parsing: budgets. |
| [backend/app/api/v1/events.py](backend/app/api/v1/events.py) | HTTP routes/dependencies/query parsing: events. |
| [backend/app/api/v1/forecast.py](backend/app/api/v1/forecast.py) | HTTP routes/dependencies/query parsing: forecast. |
| [backend/app/api/v1/health.py](backend/app/api/v1/health.py) | HTTP routes/dependencies/query parsing: health. |
| [backend/app/api/v1/integrations.py](backend/app/api/v1/integrations.py) | HTTP routes/dependencies/query parsing: integrations. |
| [backend/app/api/v1/inventory.py](backend/app/api/v1/inventory.py) | HTTP routes/dependencies/query parsing: inventory. |
| [backend/app/api/v1/jobs.py](backend/app/api/v1/jobs.py) | HTTP routes/dependencies/query parsing: jobs. |
| [backend/app/api/v1/locations.py](backend/app/api/v1/locations.py) | HTTP routes/dependencies/query parsing: locations. |
| [backend/app/api/v1/notifications.py](backend/app/api/v1/notifications.py) | HTTP routes/dependencies/query parsing: notifications. |
| [backend/app/api/v1/organizations.py](backend/app/api/v1/organizations.py) | HTTP routes/dependencies/query parsing: organizations. |
| [backend/app/api/v1/reports.py](backend/app/api/v1/reports.py) | HTTP routes/dependencies/query parsing: reports. |
| [backend/app/api/v1/router.py](backend/app/api/v1/router.py) | HTTP routes/dependencies/query parsing: router. |
| [backend/app/api/v1/runway.py](backend/app/api/v1/runway.py) | HTTP routes/dependencies/query parsing: runway. |
| [backend/app/api/v1/transactions.py](backend/app/api/v1/transactions.py) | HTTP routes/dependencies/query parsing: transactions. |
| [backend/app/api/v1/workforce/__init__.py](backend/app/api/v1/workforce/__init__.py) | HTTP routes/dependencies/query parsing:   init  . |
| [backend/app/api/v1/workforce/announcements.py](backend/app/api/v1/workforce/announcements.py) | HTTP routes/dependencies/query parsing: announcements. |
| [backend/app/api/v1/workforce/attendance.py](backend/app/api/v1/workforce/attendance.py) | HTTP routes/dependencies/query parsing: attendance. |
| [backend/app/api/v1/workforce/corrections.py](backend/app/api/v1/workforce/corrections.py) | HTTP routes/dependencies/query parsing: corrections. |
| [backend/app/api/v1/workforce/departments.py](backend/app/api/v1/workforce/departments.py) | HTTP routes/dependencies/query parsing: departments. |
| [backend/app/api/v1/workforce/employees.py](backend/app/api/v1/workforce/employees.py) | HTTP routes/dependencies/query parsing: employees. |
| [backend/app/api/v1/workforce/hr_admin.py](backend/app/api/v1/workforce/hr_admin.py) | HTTP routes/dependencies/query parsing: hr admin. |
| [backend/app/api/v1/workforce/intelligence.py](backend/app/api/v1/workforce/intelligence.py) | HTTP routes/dependencies/query parsing: intelligence. |
| [backend/app/api/v1/workforce/leave.py](backend/app/api/v1/workforce/leave.py) | HTTP routes/dependencies/query parsing: leave. |
| [backend/app/api/v1/workforce/payroll.py](backend/app/api/v1/workforce/payroll.py) | HTTP routes/dependencies/query parsing: payroll. |
| [backend/app/api/v1/workforce/router.py](backend/app/api/v1/workforce/router.py) | HTTP routes/dependencies/query parsing: router. |
| [backend/app/api/v1/workforce/shifts.py](backend/app/api/v1/workforce/shifts.py) | HTTP routes/dependencies/query parsing: shifts. |
| [backend/app/api/v1/workforce/titles.py](backend/app/api/v1/workforce/titles.py) | HTTP routes/dependencies/query parsing: titles. |
| [backend/app/core/auth_lockout.py](backend/app/core/auth_lockout.py) | Python backend/operational/runtime/load tool: auth lockout. |
| [backend/app/core/config.py](backend/app/core/config.py) | Python backend/operational/runtime/load tool: config. |
| [backend/app/core/error_envelope.py](backend/app/core/error_envelope.py) | Python backend/operational/runtime/load tool: error envelope. |
| [backend/app/core/logging.py](backend/app/core/logging.py) | Python backend/operational/runtime/load tool: logging. |
| [backend/app/core/mfa.py](backend/app/core/mfa.py) | Python backend/operational/runtime/load tool: mfa. |
| [backend/app/core/middleware.py](backend/app/core/middleware.py) | Python backend/operational/runtime/load tool: middleware. |
| [backend/app/core/observability.py](backend/app/core/observability.py) | Python backend/operational/runtime/load tool: observability. |
| [backend/app/core/pii_crypto.py](backend/app/core/pii_crypto.py) | Python backend/operational/runtime/load tool: pii crypto. |
| [backend/app/core/rate_limit.py](backend/app/core/rate_limit.py) | Python backend/operational/runtime/load tool: rate limit. |
| [backend/app/core/security.py](backend/app/core/security.py) | Python backend/operational/runtime/load tool: security. |
| [backend/app/core/slo_metrics.py](backend/app/core/slo_metrics.py) | Python backend/operational/runtime/load tool: slo metrics. |
| [backend/app/db/base.py](backend/app/db/base.py) | Python backend/operational/runtime/load tool: base. |
| [backend/app/db/migrations_utils.py](backend/app/db/migrations_utils.py) | Python backend/operational/runtime/load tool: migrations utils. |
| [backend/app/db/session.py](backend/app/db/session.py) | Python backend/operational/runtime/load tool: session. |
| [backend/app/domain/__init__.py](backend/app/domain/__init__.py) | Python backend/operational/runtime/load tool:   init  . |
| [backend/app/domain/models/__init__.py](backend/app/domain/models/__init__.py) | ORM model/enum/mixin:   init  . |
| [backend/app/domain/models/account_confirmation_token.py](backend/app/domain/models/account_confirmation_token.py) | ORM model/enum/mixin: account confirmation token. |
| [backend/app/domain/models/ai_chat_message.py](backend/app/domain/models/ai_chat_message.py) | ORM model/enum/mixin: ai chat message. |
| [backend/app/domain/models/ai_chat_session.py](backend/app/domain/models/ai_chat_session.py) | ORM model/enum/mixin: ai chat session. |
| [backend/app/domain/models/alert.py](backend/app/domain/models/alert.py) | ORM model/enum/mixin: alert. |
| [backend/app/domain/models/audit_log.py](backend/app/domain/models/audit_log.py) | ORM model/enum/mixin: audit log. |
| [backend/app/domain/models/bank_account.py](backend/app/domain/models/bank_account.py) | ORM model/enum/mixin: bank account. |
| [backend/app/domain/models/bank_connection.py](backend/app/domain/models/bank_connection.py) | ORM model/enum/mixin: bank connection. |
| [backend/app/domain/models/bank_sync_cursor.py](backend/app/domain/models/bank_sync_cursor.py) | ORM model/enum/mixin: bank sync cursor. |
| [backend/app/domain/models/bank_sync_run.py](backend/app/domain/models/bank_sync_run.py) | ORM model/enum/mixin: bank sync run. |
| [backend/app/domain/models/bank_synced_transaction.py](backend/app/domain/models/bank_synced_transaction.py) | ORM model/enum/mixin: bank synced transaction. |
| [backend/app/domain/models/budget.py](backend/app/domain/models/budget.py) | ORM model/enum/mixin: budget. |
| [backend/app/domain/models/category.py](backend/app/domain/models/category.py) | ORM model/enum/mixin: category. |
| [backend/app/domain/models/dead_letter_event.py](backend/app/domain/models/dead_letter_event.py) | ORM model/enum/mixin: dead letter event. |
| [backend/app/domain/models/deletion_request.py](backend/app/domain/models/deletion_request.py) | ORM model/enum/mixin: deletion request. |
| [backend/app/domain/models/enums.py](backend/app/domain/models/enums.py) | ORM model/enum/mixin: enums. |
| [backend/app/domain/models/forecast.py](backend/app/domain/models/forecast.py) | ORM model/enum/mixin: forecast. |
| [backend/app/domain/models/idempotency_key.py](backend/app/domain/models/idempotency_key.py) | ORM model/enum/mixin: idempotency key. |
| [backend/app/domain/models/import_mapping_profile.py](backend/app/domain/models/import_mapping_profile.py) | ORM model/enum/mixin: import mapping profile. |
| [backend/app/domain/models/inventory_item.py](backend/app/domain/models/inventory_item.py) | ORM model/enum/mixin: inventory item. |
| [backend/app/domain/models/inventory_purchase_order.py](backend/app/domain/models/inventory_purchase_order.py) | ORM model/enum/mixin: inventory purchase order. |
| [backend/app/domain/models/inventory_sales_velocity.py](backend/app/domain/models/inventory_sales_velocity.py) | ORM model/enum/mixin: inventory sales velocity. |
| [backend/app/domain/models/inventory_stock_event.py](backend/app/domain/models/inventory_stock_event.py) | ORM model/enum/mixin: inventory stock event. |
| [backend/app/domain/models/inventory_stock_level.py](backend/app/domain/models/inventory_stock_level.py) | ORM model/enum/mixin: inventory stock level. |
| [backend/app/domain/models/job_state.py](backend/app/domain/models/job_state.py) | ORM model/enum/mixin: job state. |
| [backend/app/domain/models/location.py](backend/app/domain/models/location.py) | ORM model/enum/mixin: location. |
| [backend/app/domain/models/membership.py](backend/app/domain/models/membership.py) | ORM model/enum/mixin: membership. |
| [backend/app/domain/models/mixins.py](backend/app/domain/models/mixins.py) | ORM model/enum/mixin: mixins. |
| [backend/app/domain/models/monthly_aggregate.py](backend/app/domain/models/monthly_aggregate.py) | ORM model/enum/mixin: monthly aggregate. |
| [backend/app/domain/models/notification.py](backend/app/domain/models/notification.py) | ORM model/enum/mixin: notification. |
| [backend/app/domain/models/organization.py](backend/app/domain/models/organization.py) | ORM model/enum/mixin: organization. |
| [backend/app/domain/models/organization_billing.py](backend/app/domain/models/organization_billing.py) | ORM model/enum/mixin: organization billing. |
| [backend/app/domain/models/organization_invite.py](backend/app/domain/models/organization_invite.py) | ORM model/enum/mixin: organization invite. |
| [backend/app/domain/models/organization_plan.py](backend/app/domain/models/organization_plan.py) | ORM model/enum/mixin: organization plan. |
| [backend/app/domain/models/organization_setting.py](backend/app/domain/models/organization_setting.py) | ORM model/enum/mixin: organization setting. |
| [backend/app/domain/models/outbox_event.py](backend/app/domain/models/outbox_event.py) | ORM model/enum/mixin: outbox event. |
| [backend/app/domain/models/payment_ledger_entry.py](backend/app/domain/models/payment_ledger_entry.py) | ORM model/enum/mixin: payment ledger entry. |
| [backend/app/domain/models/payment_processor_connection.py](backend/app/domain/models/payment_processor_connection.py) | ORM model/enum/mixin: payment processor connection. |
| [backend/app/domain/models/payment_webhook_event.py](backend/app/domain/models/payment_webhook_event.py) | ORM model/enum/mixin: payment webhook event. |
| [backend/app/domain/models/report.py](backend/app/domain/models/report.py) | ORM model/enum/mixin: report. |
| [backend/app/domain/models/schedule_control.py](backend/app/domain/models/schedule_control.py) | ORM model/enum/mixin: schedule control. |
| [backend/app/domain/models/token_session.py](backend/app/domain/models/token_session.py) | ORM model/enum/mixin: token session. |
| [backend/app/domain/models/transaction.py](backend/app/domain/models/transaction.py) | ORM model/enum/mixin: transaction. |
| [backend/app/domain/models/transaction_import.py](backend/app/domain/models/transaction_import.py) | ORM model/enum/mixin: transaction import. |
| [backend/app/domain/models/usage_meter.py](backend/app/domain/models/usage_meter.py) | ORM model/enum/mixin: usage meter. |
| [backend/app/domain/models/user.py](backend/app/domain/models/user.py) | ORM model/enum/mixin: user. |
| [backend/app/domain/models/workforce_announcement.py](backend/app/domain/models/workforce_announcement.py) | ORM model/enum/mixin: workforce announcement. |
| [backend/app/domain/models/workforce_announcement_delivery.py](backend/app/domain/models/workforce_announcement_delivery.py) | ORM model/enum/mixin: workforce announcement delivery. |
| [backend/app/domain/models/workforce_announcement_receipt.py](backend/app/domain/models/workforce_announcement_receipt.py) | ORM model/enum/mixin: workforce announcement receipt. |
| [backend/app/domain/models/workforce_announcement_template.py](backend/app/domain/models/workforce_announcement_template.py) | ORM model/enum/mixin: workforce announcement template. |
| [backend/app/domain/models/workforce_attendance_correction.py](backend/app/domain/models/workforce_attendance_correction.py) | ORM model/enum/mixin: workforce attendance correction. |
| [backend/app/domain/models/workforce_attendance_record.py](backend/app/domain/models/workforce_attendance_record.py) | ORM model/enum/mixin: workforce attendance record. |
| [backend/app/domain/models/workforce_checklist_item.py](backend/app/domain/models/workforce_checklist_item.py) | ORM model/enum/mixin: workforce checklist item. |
| [backend/app/domain/models/workforce_department.py](backend/app/domain/models/workforce_department.py) | ORM model/enum/mixin: workforce department. |
| [backend/app/domain/models/workforce_document.py](backend/app/domain/models/workforce_document.py) | ORM model/enum/mixin: workforce document. |
| [backend/app/domain/models/workforce_employee.py](backend/app/domain/models/workforce_employee.py) | ORM model/enum/mixin: workforce employee. |
| [backend/app/domain/models/workforce_leave_balance.py](backend/app/domain/models/workforce_leave_balance.py) | ORM model/enum/mixin: workforce leave balance. |
| [backend/app/domain/models/workforce_leave_request.py](backend/app/domain/models/workforce_leave_request.py) | ORM model/enum/mixin: workforce leave request. |
| [backend/app/domain/models/workforce_leave_type.py](backend/app/domain/models/workforce_leave_type.py) | ORM model/enum/mixin: workforce leave type. |
| [backend/app/domain/models/workforce_payroll_adjustment.py](backend/app/domain/models/workforce_payroll_adjustment.py) | ORM model/enum/mixin: workforce payroll adjustment. |
| [backend/app/domain/models/workforce_payroll_entry.py](backend/app/domain/models/workforce_payroll_entry.py) | ORM model/enum/mixin: workforce payroll entry. |
| [backend/app/domain/models/workforce_payroll_period.py](backend/app/domain/models/workforce_payroll_period.py) | ORM model/enum/mixin: workforce payroll period. |
| [backend/app/domain/models/workforce_policy.py](backend/app/domain/models/workforce_policy.py) | ORM model/enum/mixin: workforce policy. |
| [backend/app/domain/models/workforce_policy_ack.py](backend/app/domain/models/workforce_policy_ack.py) | ORM model/enum/mixin: workforce policy ack. |
| [backend/app/domain/models/workforce_shift.py](backend/app/domain/models/workforce_shift.py) | ORM model/enum/mixin: workforce shift. |
| [backend/app/domain/models/workforce_shift_assignment.py](backend/app/domain/models/workforce_shift_assignment.py) | ORM model/enum/mixin: workforce shift assignment. |
| [backend/app/domain/models/workforce_title.py](backend/app/domain/models/workforce_title.py) | ORM model/enum/mixin: workforce title. |
| [backend/app/domain/repos/__init__.py](backend/app/domain/repos/__init__.py) | Queries/persistence:   init  . |
| [backend/app/domain/repos/ai_chat_repo.py](backend/app/domain/repos/ai_chat_repo.py) | Queries/persistence: ai chat repo. |
| [backend/app/domain/repos/alerts_repo.py](backend/app/domain/repos/alerts_repo.py) | Queries/persistence: alerts repo. |
| [backend/app/domain/repos/analytics_repo.py](backend/app/domain/repos/analytics_repo.py) | Queries/persistence: analytics repo. |
| [backend/app/domain/repos/audit_repo.py](backend/app/domain/repos/audit_repo.py) | Queries/persistence: audit repo. |
| [backend/app/domain/repos/auth_repo.py](backend/app/domain/repos/auth_repo.py) | Queries/persistence: auth repo. |
| [backend/app/domain/repos/bank_repo.py](backend/app/domain/repos/bank_repo.py) | Queries/persistence: bank repo. |
| [backend/app/domain/repos/budget_repo.py](backend/app/domain/repos/budget_repo.py) | Queries/persistence: budget repo. |
| [backend/app/domain/repos/dead_letter_repo.py](backend/app/domain/repos/dead_letter_repo.py) | Queries/persistence: dead letter repo. |
| [backend/app/domain/repos/deletion_repo.py](backend/app/domain/repos/deletion_repo.py) | Queries/persistence: deletion repo. |
| [backend/app/domain/repos/forecast_repo.py](backend/app/domain/repos/forecast_repo.py) | Queries/persistence: forecast repo. |
| [backend/app/domain/repos/idempotency_repo.py](backend/app/domain/repos/idempotency_repo.py) | Queries/persistence: idempotency repo. |
| [backend/app/domain/repos/import_profile_repo.py](backend/app/domain/repos/import_profile_repo.py) | Queries/persistence: import profile repo. |
| [backend/app/domain/repos/import_repo.py](backend/app/domain/repos/import_repo.py) | Queries/persistence: import repo. |
| [backend/app/domain/repos/inventory_repo.py](backend/app/domain/repos/inventory_repo.py) | Queries/persistence: inventory repo. |
| [backend/app/domain/repos/job_repo.py](backend/app/domain/repos/job_repo.py) | Queries/persistence: job repo. |
| [backend/app/domain/repos/location_repo.py](backend/app/domain/repos/location_repo.py) | Queries/persistence: location repo. |
| [backend/app/domain/repos/notification_repo.py](backend/app/domain/repos/notification_repo.py) | Queries/persistence: notification repo. |
| [backend/app/domain/repos/org_repo.py](backend/app/domain/repos/org_repo.py) | Queries/persistence: org repo. |
| [backend/app/domain/repos/outbox_repo.py](backend/app/domain/repos/outbox_repo.py) | Queries/persistence: outbox repo. |
| [backend/app/domain/repos/payment_repo.py](backend/app/domain/repos/payment_repo.py) | Queries/persistence: payment repo. |
| [backend/app/domain/repos/plan_repo.py](backend/app/domain/repos/plan_repo.py) | Queries/persistence: plan repo. |
| [backend/app/domain/repos/report_repo.py](backend/app/domain/repos/report_repo.py) | Queries/persistence: report repo. |
| [backend/app/domain/repos/schedule_repo.py](backend/app/domain/repos/schedule_repo.py) | Queries/persistence: schedule repo. |
| [backend/app/domain/repos/transaction_repo.py](backend/app/domain/repos/transaction_repo.py) | Queries/persistence: transaction repo. |
| [backend/app/domain/repos/workforce_announcement_delivery_repo.py](backend/app/domain/repos/workforce_announcement_delivery_repo.py) | Queries/persistence: workforce announcement delivery repo. |
| [backend/app/domain/repos/workforce_announcement_repo.py](backend/app/domain/repos/workforce_announcement_repo.py) | Queries/persistence: workforce announcement repo. |
| [backend/app/domain/repos/workforce_announcement_template_repo.py](backend/app/domain/repos/workforce_announcement_template_repo.py) | Queries/persistence: workforce announcement template repo. |
| [backend/app/domain/repos/workforce_attendance_repo.py](backend/app/domain/repos/workforce_attendance_repo.py) | Queries/persistence: workforce attendance repo. |
| [backend/app/domain/repos/workforce_department_repo.py](backend/app/domain/repos/workforce_department_repo.py) | Queries/persistence: workforce department repo. |
| [backend/app/domain/repos/workforce_employee_repo.py](backend/app/domain/repos/workforce_employee_repo.py) | Queries/persistence: workforce employee repo. |
| [backend/app/domain/repos/workforce_hr_repo.py](backend/app/domain/repos/workforce_hr_repo.py) | Queries/persistence: workforce hr repo. |
| [backend/app/domain/repos/workforce_leave_balance_repo.py](backend/app/domain/repos/workforce_leave_balance_repo.py) | Queries/persistence: workforce leave balance repo. |
| [backend/app/domain/repos/workforce_leave_request_repo.py](backend/app/domain/repos/workforce_leave_request_repo.py) | Queries/persistence: workforce leave request repo. |
| [backend/app/domain/repos/workforce_leave_type_repo.py](backend/app/domain/repos/workforce_leave_type_repo.py) | Queries/persistence: workforce leave type repo. |
| [backend/app/domain/repos/workforce_payroll_repo.py](backend/app/domain/repos/workforce_payroll_repo.py) | Queries/persistence: workforce payroll repo. |
| [backend/app/domain/repos/workforce_shift_repo.py](backend/app/domain/repos/workforce_shift_repo.py) | Queries/persistence: workforce shift repo. |
| [backend/app/domain/repos/workforce_title_repo.py](backend/app/domain/repos/workforce_title_repo.py) | Queries/persistence: workforce title repo. |
| [backend/app/domain/schemas/__init__.py](backend/app/domain/schemas/__init__.py) | Pydantic contracts:   init  . |
| [backend/app/domain/schemas/ai.py](backend/app/domain/schemas/ai.py) | Pydantic contracts: ai. |
| [backend/app/domain/schemas/alerts.py](backend/app/domain/schemas/alerts.py) | Pydantic contracts: alerts. |
| [backend/app/domain/schemas/analytics.py](backend/app/domain/schemas/analytics.py) | Pydantic contracts: analytics. |
| [backend/app/domain/schemas/auth.py](backend/app/domain/schemas/auth.py) | Pydantic contracts: auth. |
| [backend/app/domain/schemas/billing.py](backend/app/domain/schemas/billing.py) | Pydantic contracts: billing. |
| [backend/app/domain/schemas/budget.py](backend/app/domain/schemas/budget.py) | Pydantic contracts: budget. |
| [backend/app/domain/schemas/common.py](backend/app/domain/schemas/common.py) | Pydantic contracts: common. |
| [backend/app/domain/schemas/forecast.py](backend/app/domain/schemas/forecast.py) | Pydantic contracts: forecast. |
| [backend/app/domain/schemas/integrations.py](backend/app/domain/schemas/integrations.py) | Pydantic contracts: integrations. |
| [backend/app/domain/schemas/inventory.py](backend/app/domain/schemas/inventory.py) | Pydantic contracts: inventory. |
| [backend/app/domain/schemas/job.py](backend/app/domain/schemas/job.py) | Pydantic contracts: job. |
| [backend/app/domain/schemas/location.py](backend/app/domain/schemas/location.py) | Pydantic contracts: location. |
| [backend/app/domain/schemas/notification.py](backend/app/domain/schemas/notification.py) | Pydantic contracts: notification. |
| [backend/app/domain/schemas/operations.py](backend/app/domain/schemas/operations.py) | Pydantic contracts: operations. |
| [backend/app/domain/schemas/organization.py](backend/app/domain/schemas/organization.py) | Pydantic contracts: organization. |
| [backend/app/domain/schemas/privacy.py](backend/app/domain/schemas/privacy.py) | Pydantic contracts: privacy. |
| [backend/app/domain/schemas/reports.py](backend/app/domain/schemas/reports.py) | Pydantic contracts: reports. |
| [backend/app/domain/schemas/transaction.py](backend/app/domain/schemas/transaction.py) | Pydantic contracts: transaction. |
| [backend/app/domain/schemas/workforce.py](backend/app/domain/schemas/workforce.py) | Pydantic contracts: workforce. |
| [backend/app/domain/schemas/workforce_announcement.py](backend/app/domain/schemas/workforce_announcement.py) | Pydantic contracts: workforce announcement. |
| [backend/app/domain/schemas/workforce_attendance.py](backend/app/domain/schemas/workforce_attendance.py) | Pydantic contracts: workforce attendance. |
| [backend/app/domain/schemas/workforce_hr.py](backend/app/domain/schemas/workforce_hr.py) | Pydantic contracts: workforce hr. |
| [backend/app/domain/schemas/workforce_intelligence.py](backend/app/domain/schemas/workforce_intelligence.py) | Pydantic contracts: workforce intelligence. |
| [backend/app/domain/schemas/workforce_leave.py](backend/app/domain/schemas/workforce_leave.py) | Pydantic contracts: workforce leave. |
| [backend/app/domain/schemas/workforce_payroll.py](backend/app/domain/schemas/workforce_payroll.py) | Pydantic contracts: workforce payroll. |
| [backend/app/domain/services/__init__.py](backend/app/domain/services/__init__.py) | Business rules/orchestration:   init  . |
| [backend/app/domain/services/ai_chat_service.py](backend/app/domain/services/ai_chat_service.py) | Business rules/orchestration: ai chat service. |
| [backend/app/domain/services/ai_grounding_validator.py](backend/app/domain/services/ai_grounding_validator.py) | Business rules/orchestration: ai grounding validator. |
| [backend/app/domain/services/ai_service.py](backend/app/domain/services/ai_service.py) | Business rules/orchestration: ai service. |
| [backend/app/domain/services/alerts_refresh_service.py](backend/app/domain/services/alerts_refresh_service.py) | Business rules/orchestration: alerts refresh service. |
| [backend/app/domain/services/alerts_service.py](backend/app/domain/services/alerts_service.py) | Business rules/orchestration: alerts service. |
| [backend/app/domain/services/analytics_service.py](backend/app/domain/services/analytics_service.py) | Business rules/orchestration: analytics service. |
| [backend/app/domain/services/auth_service.py](backend/app/domain/services/auth_service.py) | Business rules/orchestration: auth service. |
| [backend/app/domain/services/bank_integration_service.py](backend/app/domain/services/bank_integration_service.py) | Business rules/orchestration: bank integration service. |
| [backend/app/domain/services/bank_provider.py](backend/app/domain/services/bank_provider.py) | Business rules/orchestration: bank provider. |
| [backend/app/domain/services/billing_service.py](backend/app/domain/services/billing_service.py) | Business rules/orchestration: billing service. |
| [backend/app/domain/services/budget_service.py](backend/app/domain/services/budget_service.py) | Business rules/orchestration: budget service. |
| [backend/app/domain/services/errors.py](backend/app/domain/services/errors.py) | Business rules/orchestration: errors. |
| [backend/app/domain/services/forecast_service.py](backend/app/domain/services/forecast_service.py) | Business rules/orchestration: forecast service. |
| [backend/app/domain/services/idempotency_service.py](backend/app/domain/services/idempotency_service.py) | Business rules/orchestration: idempotency service. |
| [backend/app/domain/services/import_profile_service.py](backend/app/domain/services/import_profile_service.py) | Business rules/orchestration: import profile service. |
| [backend/app/domain/services/inventory_service.py](backend/app/domain/services/inventory_service.py) | Business rules/orchestration: inventory service. |
| [backend/app/domain/services/job_dispatch_service.py](backend/app/domain/services/job_dispatch_service.py) | Business rules/orchestration: job dispatch service. |
| [backend/app/domain/services/location_service.py](backend/app/domain/services/location_service.py) | Business rules/orchestration: location service. |
| [backend/app/domain/services/notification_service.py](backend/app/domain/services/notification_service.py) | Business rules/orchestration: notification service. |
| [backend/app/domain/services/org_service.py](backend/app/domain/services/org_service.py) | Business rules/orchestration: org service. |
| [backend/app/domain/services/payment_integration_service.py](backend/app/domain/services/payment_integration_service.py) | Business rules/orchestration: payment integration service. |
| [backend/app/domain/services/privacy_service.py](backend/app/domain/services/privacy_service.py) | Business rules/orchestration: privacy service. |
| [backend/app/domain/services/read_cache_service.py](backend/app/domain/services/read_cache_service.py) | Business rules/orchestration: read cache service. |
| [backend/app/domain/services/report_service.py](backend/app/domain/services/report_service.py) | Business rules/orchestration: report service. |
| [backend/app/domain/services/transaction_service.py](backend/app/domain/services/transaction_service.py) | Business rules/orchestration: transaction service. |
| [backend/app/domain/services/usage_service.py](backend/app/domain/services/usage_service.py) | Business rules/orchestration: usage service. |
| [backend/app/domain/services/workforce_access_policy.py](backend/app/domain/services/workforce_access_policy.py) | Business rules/orchestration: workforce access policy. |
| [backend/app/domain/services/workforce_announcement_automation.py](backend/app/domain/services/workforce_announcement_automation.py) | Business rules/orchestration: workforce announcement automation. |
| [backend/app/domain/services/workforce_announcement_service.py](backend/app/domain/services/workforce_announcement_service.py) | Business rules/orchestration: workforce announcement service. |
| [backend/app/domain/services/workforce_attendance_service.py](backend/app/domain/services/workforce_attendance_service.py) | Business rules/orchestration: workforce attendance service. |
| [backend/app/domain/services/workforce_department_service.py](backend/app/domain/services/workforce_department_service.py) | Business rules/orchestration: workforce department service. |
| [backend/app/domain/services/workforce_employee_service.py](backend/app/domain/services/workforce_employee_service.py) | Business rules/orchestration: workforce employee service. |
| [backend/app/domain/services/workforce_hr_service.py](backend/app/domain/services/workforce_hr_service.py) | Business rules/orchestration: workforce hr service. |
| [backend/app/domain/services/workforce_intelligence_service.py](backend/app/domain/services/workforce_intelligence_service.py) | Business rules/orchestration: workforce intelligence service. |
| [backend/app/domain/services/workforce_leave_service.py](backend/app/domain/services/workforce_leave_service.py) | Business rules/orchestration: workforce leave service. |
| [backend/app/domain/services/workforce_payroll_service.py](backend/app/domain/services/workforce_payroll_service.py) | Business rules/orchestration: workforce payroll service. |
| [backend/app/domain/services/workforce_payslip_pdf.py](backend/app/domain/services/workforce_payslip_pdf.py) | Business rules/orchestration: workforce payslip pdf. |
| [backend/app/domain/services/workforce_shift_service.py](backend/app/domain/services/workforce_shift_service.py) | Business rules/orchestration: workforce shift service. |
| [backend/app/domain/services/workforce_title_service.py](backend/app/domain/services/workforce_title_service.py) | Business rules/orchestration: workforce title service. |
| [backend/app/infra/__init__.py](backend/app/infra/__init__.py) | Python backend/operational/runtime/load tool:   init  . |
| [backend/app/infra/ai_client.py](backend/app/infra/ai_client.py) | Python backend/operational/runtime/load tool: ai client. |
| [backend/app/infra/cache.py](backend/app/infra/cache.py) | Python backend/operational/runtime/load tool: cache. |
| [backend/app/infra/email.py](backend/app/infra/email.py) | Python backend/operational/runtime/load tool: email. |
| [backend/app/infra/s3.py](backend/app/infra/s3.py) | Python backend/operational/runtime/load tool: s3. |
| [backend/app/jobs/__init__.py](backend/app/jobs/__init__.py) | Celery task/configuration/tracking/runtime:   init  . |
| [backend/app/jobs/async_runtime.py](backend/app/jobs/async_runtime.py) | Celery task/configuration/tracking/runtime: async runtime. |
| [backend/app/jobs/beat_schedule.py](backend/app/jobs/beat_schedule.py) | Celery task/configuration/tracking/runtime: beat schedule. |
| [backend/app/jobs/celery_app.py](backend/app/jobs/celery_app.py) | Celery task/configuration/tracking/runtime: celery app. |
| [backend/app/jobs/task_tracking.py](backend/app/jobs/task_tracking.py) | Celery task/configuration/tracking/runtime: task tracking. |
| [backend/app/jobs/tasks/__init__.py](backend/app/jobs/tasks/__init__.py) | Celery task/configuration/tracking/runtime:   init  . |
| [backend/app/jobs/tasks/admin.py](backend/app/jobs/tasks/admin.py) | Celery task/configuration/tracking/runtime: admin. |
| [backend/app/jobs/tasks/alerts.py](backend/app/jobs/tasks/alerts.py) | Celery task/configuration/tracking/runtime: alerts. |
| [backend/app/jobs/tasks/analytics.py](backend/app/jobs/tasks/analytics.py) | Celery task/configuration/tracking/runtime: analytics. |
| [backend/app/jobs/tasks/banks.py](backend/app/jobs/tasks/banks.py) | Celery task/configuration/tracking/runtime: banks. |
| [backend/app/jobs/tasks/emails.py](backend/app/jobs/tasks/emails.py) | Celery task/configuration/tracking/runtime: emails. |
| [backend/app/jobs/tasks/forecasts.py](backend/app/jobs/tasks/forecasts.py) | Celery task/configuration/tracking/runtime: forecasts. |
| [backend/app/jobs/tasks/outbox.py](backend/app/jobs/tasks/outbox.py) | Celery task/configuration/tracking/runtime: outbox. |
| [backend/app/jobs/tasks/privacy.py](backend/app/jobs/tasks/privacy.py) | Celery task/configuration/tracking/runtime: privacy. |
| [backend/app/jobs/tasks/reports.py](backend/app/jobs/tasks/reports.py) | Celery task/configuration/tracking/runtime: reports. |
| [backend/app/jobs/tasks/workforce.py](backend/app/jobs/tasks/workforce.py) | Celery task/configuration/tracking/runtime: workforce. |
| [backend/app/main.py](backend/app/main.py) | Python backend/operational/runtime/load tool: main. |
| [backend/app/scripts_seed_categories.py](backend/app/scripts_seed_categories.py) | Python backend/operational/runtime/load tool: scripts seed categories. |
| [backend/app/tests/conftest.py](backend/app/tests/conftest.py) | Backend tests/fixtures: conftest. |
| [backend/app/tests/test_admin_operations.py](backend/app/tests/test_admin_operations.py) | Backend tests/fixtures: test admin operations. |
| [backend/app/tests/test_admin_recompute.py](backend/app/tests/test_admin_recompute.py) | Backend tests/fixtures: test admin recompute. |
| [backend/app/tests/test_ai_chat_endpoint.py](backend/app/tests/test_ai_chat_endpoint.py) | Backend tests/fixtures: test ai chat endpoint. |
| [backend/app/tests/test_ai_chat_service.py](backend/app/tests/test_ai_chat_service.py) | Backend tests/fixtures: test ai chat service. |
| [backend/app/tests/test_ai_grounding_validator.py](backend/app/tests/test_ai_grounding_validator.py) | Backend tests/fixtures: test ai grounding validator. |
| [backend/app/tests/test_ai_service.py](backend/app/tests/test_ai_service.py) | Backend tests/fixtures: test ai service. |
| [backend/app/tests/test_alembic_version_table_compat.py](backend/app/tests/test_alembic_version_table_compat.py) | Backend tests/fixtures: test alembic version table compat. |
| [backend/app/tests/test_alert_assignment_api.py](backend/app/tests/test_alert_assignment_api.py) | Backend tests/fixtures: test alert assignment api. |
| [backend/app/tests/test_alert_assignment_service.py](backend/app/tests/test_alert_assignment_service.py) | Backend tests/fixtures: test alert assignment service. |
| [backend/app/tests/test_alerts_anomaly_math.py](backend/app/tests/test_alerts_anomaly_math.py) | Backend tests/fixtures: test alerts anomaly math. |
| [backend/app/tests/test_alerts_budget_threshold.py](backend/app/tests/test_alerts_budget_threshold.py) | Backend tests/fixtures: test alerts budget threshold. |
| [backend/app/tests/test_alerts_inventory_stockout.py](backend/app/tests/test_alerts_inventory_stockout.py) | Backend tests/fixtures: test alerts inventory stockout. |
| [backend/app/tests/test_alerts_location_filter.py](backend/app/tests/test_alerts_location_filter.py) | Backend tests/fixtures: test alerts location filter. |
| [backend/app/tests/test_alerts_location_scoping.py](backend/app/tests/test_alerts_location_scoping.py) | Backend tests/fixtures: test alerts location scoping. |
| [backend/app/tests/test_alerts_ordering.py](backend/app/tests/test_alerts_ordering.py) | Backend tests/fixtures: test alerts ordering. |
| [backend/app/tests/test_alerts_refresh_service.py](backend/app/tests/test_alerts_refresh_service.py) | Backend tests/fixtures: test alerts refresh service. |
| [backend/app/tests/test_analytics.py](backend/app/tests/test_analytics.py) | Backend tests/fixtures: test analytics. |
| [backend/app/tests/test_analytics_budget_variance_endpoint.py](backend/app/tests/test_analytics_budget_variance_endpoint.py) | Backend tests/fixtures: test analytics budget variance endpoint. |
| [backend/app/tests/test_analytics_location_benchmark_endpoint.py](backend/app/tests/test_analytics_location_benchmark_endpoint.py) | Backend tests/fixtures: test analytics location benchmark endpoint. |
| [backend/app/tests/test_analytics_recompute_endpoint.py](backend/app/tests/test_analytics_recompute_endpoint.py) | Backend tests/fixtures: test analytics recompute endpoint. |
| [backend/app/tests/test_api_integration_live.py](backend/app/tests/test_api_integration_live.py) | Backend tests/fixtures: test api integration live. |
| [backend/app/tests/test_auth.py](backend/app/tests/test_auth.py) | Backend tests/fixtures: test auth. |
| [backend/app/tests/test_auth_cookie_integration_live.py](backend/app/tests/test_auth_cookie_integration_live.py) | Backend tests/fixtures: test auth cookie integration live. |
| [backend/app/tests/test_auth_delete_account_endpoint.py](backend/app/tests/test_auth_delete_account_endpoint.py) | Backend tests/fixtures: test auth delete account endpoint. |
| [backend/app/tests/test_auth_dev_confirmation_endpoint.py](backend/app/tests/test_auth_dev_confirmation_endpoint.py) | Backend tests/fixtures: test auth dev confirmation endpoint. |
| [backend/app/tests/test_auth_lockout_endpoint.py](backend/app/tests/test_auth_lockout_endpoint.py) | Backend tests/fixtures: test auth lockout endpoint. |
| [backend/app/tests/test_auth_lockout_metrics.py](backend/app/tests/test_auth_lockout_metrics.py) | Backend tests/fixtures: test auth lockout metrics. |
| [backend/app/tests/test_auth_mfa_service.py](backend/app/tests/test_auth_mfa_service.py) | Backend tests/fixtures: test auth mfa service. |
| [backend/app/tests/test_auth_mfa_session_endpoints.py](backend/app/tests/test_auth_mfa_session_endpoints.py) | Backend tests/fixtures: test auth mfa session endpoints. |
| [backend/app/tests/test_auth_owner_mfa_policy.py](backend/app/tests/test_auth_owner_mfa_policy.py) | Backend tests/fixtures: test auth owner mfa policy. |
| [backend/app/tests/test_auth_refresh_reuse.py](backend/app/tests/test_auth_refresh_reuse.py) | Backend tests/fixtures: test auth refresh reuse. |
| [backend/app/tests/test_auth_registration_confirmation.py](backend/app/tests/test_auth_registration_confirmation.py) | Backend tests/fixtures: test auth registration confirmation. |
| [backend/app/tests/test_auth_session_management_service.py](backend/app/tests/test_auth_session_management_service.py) | Backend tests/fixtures: test auth session management service. |
| [backend/app/tests/test_auth_session_tokens.py](backend/app/tests/test_auth_session_tokens.py) | Backend tests/fixtures: test auth session tokens. |
| [backend/app/tests/test_bank_provider.py](backend/app/tests/test_bank_provider.py) | Backend tests/fixtures: test bank provider. |
| [backend/app/tests/test_banks_tasks.py](backend/app/tests/test_banks_tasks.py) | Backend tests/fixtures: test banks tasks. |
| [backend/app/tests/test_budget_service.py](backend/app/tests/test_budget_service.py) | Backend tests/fixtures: test budget service. |
| [backend/app/tests/test_budgets_endpoint.py](backend/app/tests/test_budgets_endpoint.py) | Backend tests/fixtures: test budgets endpoint. |
| [backend/app/tests/test_bulk_remap_recompute.py](backend/app/tests/test_bulk_remap_recompute.py) | Backend tests/fixtures: test bulk remap recompute. |
| [backend/app/tests/test_celery_task_registration.py](backend/app/tests/test_celery_task_registration.py) | Backend tests/fixtures: test celery task registration. |
| [backend/app/tests/test_csv_import.py](backend/app/tests/test_csv_import.py) | Backend tests/fixtures: test csv import. |
| [backend/app/tests/test_csv_import_duplicates.py](backend/app/tests/test_csv_import_duplicates.py) | Backend tests/fixtures: test csv import duplicates. |
| [backend/app/tests/test_db_session_pool_config.py](backend/app/tests/test_db_session_pool_config.py) | Backend tests/fixtures: test db session pool config. |
| [backend/app/tests/test_dead_letter_model.py](backend/app/tests/test_dead_letter_model.py) | Backend tests/fixtures: test dead letter model. |
| [backend/app/tests/test_error_envelope.py](backend/app/tests/test_error_envelope.py) | Backend tests/fixtures: test error envelope. |
| [backend/app/tests/test_events_endpoint.py](backend/app/tests/test_events_endpoint.py) | Backend tests/fixtures: test events endpoint. |
| [backend/app/tests/test_health_endpoint.py](backend/app/tests/test_health_endpoint.py) | Backend tests/fixtures: test health endpoint. |
| [backend/app/tests/test_https_enforcement.py](backend/app/tests/test_https_enforcement.py) | Backend tests/fixtures: test https enforcement. |
| [backend/app/tests/test_idempotency_service.py](backend/app/tests/test_idempotency_service.py) | Backend tests/fixtures: test idempotency service. |
| [backend/app/tests/test_import_mapping_profile_model.py](backend/app/tests/test_import_mapping_profile_model.py) | Backend tests/fixtures: test import mapping profile model. |
| [backend/app/tests/test_import_profiles_endpoint.py](backend/app/tests/test_import_profiles_endpoint.py) | Backend tests/fixtures: test import profiles endpoint. |
| [backend/app/tests/test_integrations_endpoint.py](backend/app/tests/test_integrations_endpoint.py) | Backend tests/fixtures: test integrations endpoint. |
| [backend/app/tests/test_integrations_payments_webhook.py](backend/app/tests/test_integrations_payments_webhook.py) | Backend tests/fixtures: test integrations payments webhook. |
| [backend/app/tests/test_integrations_webhook.py](backend/app/tests/test_integrations_webhook.py) | Backend tests/fixtures: test integrations webhook. |
| [backend/app/tests/test_inventory_endpoint.py](backend/app/tests/test_inventory_endpoint.py) | Backend tests/fixtures: test inventory endpoint. |
| [backend/app/tests/test_inventory_repo_duplicate_tolerance.py](backend/app/tests/test_inventory_repo_duplicate_tolerance.py) | Backend tests/fixtures: test inventory repo duplicate tolerance. |
| [backend/app/tests/test_inventory_service.py](backend/app/tests/test_inventory_service.py) | Backend tests/fixtures: test inventory service. |
| [backend/app/tests/test_job_repo_race.py](backend/app/tests/test_job_repo_race.py) | Backend tests/fixtures: test job repo race. |
| [backend/app/tests/test_jobs_commands.py](backend/app/tests/test_jobs_commands.py) | Backend tests/fixtures: test jobs commands. |
| [backend/app/tests/test_jobs_endpoint.py](backend/app/tests/test_jobs_endpoint.py) | Backend tests/fixtures: test jobs endpoint. |
| [backend/app/tests/test_location_service.py](backend/app/tests/test_location_service.py) | Backend tests/fixtures: test location service. |
| [backend/app/tests/test_locations_endpoint.py](backend/app/tests/test_locations_endpoint.py) | Backend tests/fixtures: test locations endpoint. |
| [backend/app/tests/test_mfa_utils.py](backend/app/tests/test_mfa_utils.py) | Backend tests/fixtures: test mfa utils. |
| [backend/app/tests/test_notifications_endpoint.py](backend/app/tests/test_notifications_endpoint.py) | Backend tests/fixtures: test notifications endpoint. |
| [backend/app/tests/test_org_billing_endpoint.py](backend/app/tests/test_org_billing_endpoint.py) | Backend tests/fixtures: test org billing endpoint. |
| [backend/app/tests/test_org_security_policy_endpoint.py](backend/app/tests/test_org_security_policy_endpoint.py) | Backend tests/fixtures: test org security policy endpoint. |
| [backend/app/tests/test_org_settings_validation.py](backend/app/tests/test_org_settings_validation.py) | Backend tests/fixtures: test org settings validation. |
| [backend/app/tests/test_organizations_invite_visibility.py](backend/app/tests/test_organizations_invite_visibility.py) | Backend tests/fixtures: test organizations invite visibility. |
| [backend/app/tests/test_outbox.py](backend/app/tests/test_outbox.py) | Backend tests/fixtures: test outbox. |
| [backend/app/tests/test_outbox_dead_letter.py](backend/app/tests/test_outbox_dead_letter.py) | Backend tests/fixtures: test outbox dead letter. |
| [backend/app/tests/test_owner_policy_deps.py](backend/app/tests/test_owner_policy_deps.py) | Backend tests/fixtures: test owner policy deps. |
| [backend/app/tests/test_payment_integration_service.py](backend/app/tests/test_payment_integration_service.py) | Backend tests/fixtures: test payment integration service. |
| [backend/app/tests/test_period_month_query.py](backend/app/tests/test_period_month_query.py) | Backend tests/fixtures: test period month query. |
| [backend/app/tests/test_pii_crypto.py](backend/app/tests/test_pii_crypto.py) | Backend tests/fixtures: test pii crypto. |
| [backend/app/tests/test_plaid_sandbox_live.py](backend/app/tests/test_plaid_sandbox_live.py) | Backend tests/fixtures: test plaid sandbox live. |
| [backend/app/tests/test_plan_repo_usage_race.py](backend/app/tests/test_plan_repo_usage_race.py) | Backend tests/fixtures: test plan repo usage race. |
| [backend/app/tests/test_plan_usage_endpoint.py](backend/app/tests/test_plan_usage_endpoint.py) | Backend tests/fixtures: test plan usage endpoint. |
| [backend/app/tests/test_rbac.py](backend/app/tests/test_rbac.py) | Backend tests/fixtures: test rbac. |
| [backend/app/tests/test_read_caching_endpoints.py](backend/app/tests/test_read_caching_endpoints.py) | Backend tests/fixtures: test read caching endpoints. |
| [backend/app/tests/test_report_service_roundtrip.py](backend/app/tests/test_report_service_roundtrip.py) | Backend tests/fixtures: test report service roundtrip. |
| [backend/app/tests/test_reports_endpoint.py](backend/app/tests/test_reports_endpoint.py) | Backend tests/fixtures: test reports endpoint. |
| [backend/app/tests/test_reports_idempotent.py](backend/app/tests/test_reports_idempotent.py) | Backend tests/fixtures: test reports idempotent. |
| [backend/app/tests/test_reports_task.py](backend/app/tests/test_reports_task.py) | Backend tests/fixtures: test reports task. |
| [backend/app/tests/test_runway.py](backend/app/tests/test_runway.py) | Backend tests/fixtures: test runway. |
| [backend/app/tests/test_security_tokens.py](backend/app/tests/test_security_tokens.py) | Backend tests/fixtures: test security tokens. |
| [backend/app/tests/test_slo_metrics.py](backend/app/tests/test_slo_metrics.py) | Backend tests/fixtures: test slo metrics. |
| [backend/app/tests/test_stripe_sandbox_live.py](backend/app/tests/test_stripe_sandbox_live.py) | Backend tests/fixtures: test stripe sandbox live. |
| [backend/app/tests/test_task_tracking.py](backend/app/tests/test_task_tracking.py) | Backend tests/fixtures: test task tracking. |
| [backend/app/tests/test_tenant_isolation.py](backend/app/tests/test_tenant_isolation.py) | Backend tests/fixtures: test tenant isolation. |
| [backend/app/tests/test_transaction_import_history_endpoint.py](backend/app/tests/test_transaction_import_history_endpoint.py) | Backend tests/fixtures: test transaction import history endpoint. |
| [backend/app/tests/test_transactions.py](backend/app/tests/test_transactions.py) | Backend tests/fixtures: test transactions. |
| [backend/app/tests/test_transactions_alert_refresh_enqueue.py](backend/app/tests/test_transactions_alert_refresh_enqueue.py) | Backend tests/fixtures: test transactions alert refresh enqueue. |
| [backend/app/tests/test_transactions_jobs_alert_enqueue_integration.py](backend/app/tests/test_transactions_jobs_alert_enqueue_integration.py) | Backend tests/fixtures: test transactions jobs alert enqueue integration. |
| [backend/app/tests/test_usage_limits.py](backend/app/tests/test_usage_limits.py) | Backend tests/fixtures: test usage limits. |
| [backend/app/tests/test_workforce_announcement_automation.py](backend/app/tests/test_workforce_announcement_automation.py) | Backend tests/fixtures: test workforce announcement automation. |
| [backend/app/tests/test_workforce_announcement_service.py](backend/app/tests/test_workforce_announcement_service.py) | Backend tests/fixtures: test workforce announcement service. |
| [backend/app/tests/test_workforce_attendance_endpoints.py](backend/app/tests/test_workforce_attendance_endpoints.py) | Backend tests/fixtures: test workforce attendance endpoints. |
| [backend/app/tests/test_workforce_frontend_contracts.py](backend/app/tests/test_workforce_frontend_contracts.py) | Backend tests/fixtures: test workforce frontend contracts. |
| [backend/app/tests/test_workforce_leave_endpoints.py](backend/app/tests/test_workforce_leave_endpoints.py) | Backend tests/fixtures: test workforce leave endpoints. |
| [backend/app/tests/test_workforce_leave_overlap.py](backend/app/tests/test_workforce_leave_overlap.py) | Backend tests/fixtures: test workforce leave overlap. |
| [backend/app/tests/test_workforce_leave_service.py](backend/app/tests/test_workforce_leave_service.py) | Backend tests/fixtures: test workforce leave service. |
| [backend/app/tests/test_workforce_notifications.py](backend/app/tests/test_workforce_notifications.py) | Backend tests/fixtures: test workforce notifications. |
| [backend/app/tests/test_workforce_org_context_canonical.py](backend/app/tests/test_workforce_org_context_canonical.py) | Backend tests/fixtures: test workforce org context canonical. |
| [backend/app/tests/test_workforce_payroll_endpoints.py](backend/app/tests/test_workforce_payroll_endpoints.py) | Backend tests/fixtures: test workforce payroll endpoints. |
| [backend/app/tests/test_workforce_payroll_service.py](backend/app/tests/test_workforce_payroll_service.py) | Backend tests/fixtures: test workforce payroll service. |
| [backend/app/tests/test_workforce_payslip_pdf.py](backend/app/tests/test_workforce_payslip_pdf.py) | Backend tests/fixtures: test workforce payslip pdf. |
| [backend/app/tests/test_workforce_phase1_endpoints.py](backend/app/tests/test_workforce_phase1_endpoints.py) | Backend tests/fixtures: test workforce phase1 endpoints. |
| [backend/app/tests/test_workforce_phase6_hr_endpoints.py](backend/app/tests/test_workforce_phase6_hr_endpoints.py) | Backend tests/fixtures: test workforce phase6 hr endpoints. |
| [backend/app/tests/test_workforce_phase7_intelligence_endpoint.py](backend/app/tests/test_workforce_phase7_intelligence_endpoint.py) | Backend tests/fixtures: test workforce phase7 intelligence endpoint. |
| [backend/app/utils/__init__.py](backend/app/utils/__init__.py) | Python backend/operational/runtime/load tool:   init  . |
| [backend/app/utils/csv_import.py](backend/app/utils/csv_import.py) | Python backend/operational/runtime/load tool: csv import. |
| [backend/app/utils/idempotency.py](backend/app/utils/idempotency.py) | Python backend/operational/runtime/load tool: idempotency. |
| [backend/app/utils/idempotency_request.py](backend/app/utils/idempotency_request.py) | Python backend/operational/runtime/load tool: idempotency request. |
| [backend/app/utils/money.py](backend/app/utils/money.py) | Python backend/operational/runtime/load tool: money. |
| [backend/app/utils/time.py](backend/app/utils/time.py) | Python backend/operational/runtime/load tool: time. |
| [backend/docs/adr/0001-worker-choice.md](backend/docs/adr/0001-worker-choice.md) | ADR 0001: Worker choice. Sections: Decision; Why; Consequences. Historical/current guidance or proposals; compare with source. |
| [backend/docs/adr/0002-forecast-algorithm.md](backend/docs/adr/0002-forecast-algorithm.md) | ADR 0002: Forecast model. Sections: Decision; Why; Details. Historical/current guidance or proposals; compare with source. |
| [backend/docs/adr/0003-cash-balance.md](backend/docs/adr/0003-cash-balance.md) | ADR 0003: Cash balance definition. Sections: Decision; Why; Formula. Historical/current guidance or proposals; compare with source. |
| [backend/docs/adr/0004-idempotency.md](backend/docs/adr/0004-idempotency.md) | ADR 0004: Report idempotency. Sections: Decision; Why; Implementation. Historical/current guidance or proposals; compare with source. |
| [backend/docs/adr/0005-job-state-standardization.md](backend/docs/adr/0005-job-state-standardization.md) | ADR 0005: Job State Standardization. Sections: Status; Context; Decision; Consequences. Historical/current guidance or proposals; compare with source. |
| [backend/docs/adr/0006-outbox-pattern.md](backend/docs/adr/0006-outbox-pattern.md) | ADR 0006: Outbox Pattern For Notifications. Sections: Status; Context; Decision; Consequences. Historical/current guidance or proposals; compare with source. |
| [backend/docs/adr/0007-refresh-token-reuse-detection.md](backend/docs/adr/0007-refresh-token-reuse-detection.md) | ADR 0007: Refresh Token Reuse Detection. Sections: Status; Context; Decision; Consequences. Historical/current guidance or proposals; compare with source. |
| [backend/docs/adr/0008-performance-harness.md](backend/docs/adr/0008-performance-harness.md) | ADR 0008: Performance Seed + Load Harness. Sections: Status; Context; Decision; Consequences. Historical/current guidance or proposals; compare with source. |
| [backend/docs/adr/0009-plans-and-usage-metering.md](backend/docs/adr/0009-plans-and-usage-metering.md) | ADR 0009: Lightweight Plans And Usage Metering. Sections: Status; Context; Decision; Consequences. Historical/current guidance or proposals; compare with source. |
| [backend/docs/adr/0010-transaction-import-history.md](backend/docs/adr/0010-transaction-import-history.md) | ADR 0010: Transaction Import History With Error Downloads. Sections: Status; Context; Decision; Consequences. Historical/current guidance or proposals; compare with source. |
| [backend/docs/adr/0011-registration-confirmation-and-billing.md](backend/docs/adr/0011-registration-confirmation-and-billing.md) | ADR 0011: Registration Confirmation + Owner Billing Placeholder. Sections: Status; Context; Decision; Consequences. Historical/current guidance or proposals; compare with source. |
| [backend/docs/adr/0012-realtime-updates-sse-with-polling-fallback.md](backend/docs/adr/0012-realtime-updates-sse-with-polling-fallback.md) | ADR 0012: Realtime Updates via SSE with Polling Fallback. Sections: Status; Context; Decision; Consequences. Historical/current guidance or proposals; compare with source. |
| [backend/migrations/env.py](backend/migrations/env.py) | Python backend/operational/runtime/load tool: env. |
| [backend/migrations/script.py.mako](backend/migrations/script.py.mako) | Configuration/generated contract/support artifact: script.py.mako. |
| [backend/migrations/versions/0001_initial.py](backend/migrations/versions/0001_initial.py) | Alembic migration: 0001 initial. |
| [backend/migrations/versions/0002_categories.py](backend/migrations/versions/0002_categories.py) | Alembic migration: 0002 categories. |
| [backend/migrations/versions/0003_job_states.py](backend/migrations/versions/0003_job_states.py) | Alembic migration: 0003 job states. |
| [backend/migrations/versions/0004_invites_and_org_thresholds.py](backend/migrations/versions/0004_invites_and_org_thresholds.py) | Alembic migration: 0004 invites and org thresholds. |
| [backend/migrations/versions/0005_job_state_lifecycle.py](backend/migrations/versions/0005_job_state_lifecycle.py) | Alembic migration: 0005 job state lifecycle. |
| [backend/migrations/versions/0006_outbox_events.py](backend/migrations/versions/0006_outbox_events.py) | Alembic migration: 0006 outbox events. |
| [backend/migrations/versions/0007_refresh_reuse_detection.py](backend/migrations/versions/0007_refresh_reuse_detection.py) | Alembic migration: 0007 refresh reuse detection. |
| [backend/migrations/versions/0008_alerts_open_partial_index.py](backend/migrations/versions/0008_alerts_open_partial_index.py) | Alembic migration: 0008 alerts open partial index. |
| [backend/migrations/versions/0009_plans_usage_import_history.py](backend/migrations/versions/0009_plans_usage_import_history.py) | Alembic migration: 0009 plans usage import history. |
| [backend/migrations/versions/0010_confirm_and_billing.py](backend/migrations/versions/0010_confirm_and_billing.py) | Alembic migration: 0010 confirm and billing. |
| [backend/migrations/versions/0011_notifications_billing_and_scheduler.py](backend/migrations/versions/0011_notifications_billing_and_scheduler.py) | Alembic migration: 0011 notifications billing and scheduler. |
| [backend/migrations/versions/0012_import_mapping_profiles.py](backend/migrations/versions/0012_import_mapping_profiles.py) | Alembic migration: 0012 import mapping profiles. |
| [backend/migrations/versions/0013_tx_search_trgm_indexes.py](backend/migrations/versions/0013_tx_search_trgm_indexes.py) | Alembic migration: 0013 tx search trgm indexes. |
| [backend/migrations/versions/0014_alert_assignment_workflow.py](backend/migrations/versions/0014_alert_assignment_workflow.py) | Alembic migration: 0014 alert assignment workflow. |
| [backend/migrations/versions/0015_mfa_and_session_management.py](backend/migrations/versions/0015_mfa_and_session_management.py) | Alembic migration: 0015 mfa and session management. |
| [backend/migrations/versions/0016_mfa_recovery_codes.py](backend/migrations/versions/0016_mfa_recovery_codes.py) | Alembic migration: 0016 mfa recovery codes. |
| [backend/migrations/versions/0017_idempotency_keys.py](backend/migrations/versions/0017_idempotency_keys.py) | Alembic migration: 0017 idempotency keys. |
| [backend/migrations/versions/0018_owner_security_policy.py](backend/migrations/versions/0018_owner_security_policy.py) | Alembic migration: 0018 owner security policy. |
| [backend/migrations/versions/0019_privacy_and_deletion_baseline.py](backend/migrations/versions/0019_privacy_and_deletion_baseline.py) | Alembic migration: 0019 privacy and deletion baseline. |
| [backend/migrations/versions/0020_dead_letter_events.py](backend/migrations/versions/0020_dead_letter_events.py) | Alembic migration: 0020 dead letter events. |
| [backend/migrations/versions/0021_bank_integrations_plaid_foundation.py](backend/migrations/versions/0021_bank_integrations_plaid_foundation.py) | Alembic migration: 0021 bank integrations plaid foundation. |
| [backend/migrations/versions/0022_payment_integrations_stripe_foundation.py](backend/migrations/versions/0022_payment_integrations_stripe_foundation.py) | Alembic migration: 0022 payment integrations stripe foundation. |
| [backend/migrations/versions/0023_budgets_foundation.py](backend/migrations/versions/0023_budgets_foundation.py) | Alembic migration: 0023 budgets foundation. |
| [backend/migrations/versions/0024_org_budget_threshold_setting.py](backend/migrations/versions/0024_org_budget_threshold_setting.py) | Alembic migration: 0024 org budget threshold setting. |
| [backend/migrations/versions/0025_locations_dimension.py](backend/migrations/versions/0025_locations_dimension.py) | Alembic migration: 0025 locations dimension. |
| [backend/migrations/versions/0026_alerts_location_scope.py](backend/migrations/versions/0026_alerts_location_scope.py) | Alembic migration: 0026 alerts location scope. |
| [backend/migrations/versions/0027_inventory_forecasting_foundation.py](backend/migrations/versions/0027_inventory_forecasting_foundation.py) | Alembic migration: 0027 inventory forecasting foundation. |
| [backend/migrations/versions/0028_ai_chat_assistant_foundation.py](backend/migrations/versions/0028_ai_chat_assistant_foundation.py) | Alembic migration: 0028 ai chat assistant foundation. |
| [backend/migrations/versions/0029_workforce_phase1_foundation.py](backend/migrations/versions/0029_workforce_phase1_foundation.py) | Alembic migration: 0029 workforce phase1 foundation. |
| [backend/migrations/versions/0030_workforce_attendance_and_shifts.py](backend/migrations/versions/0030_workforce_attendance_and_shifts.py) | Alembic migration: 0030 workforce attendance and shifts. |
| [backend/migrations/versions/0031_workforce_leave.py](backend/migrations/versions/0031_workforce_leave.py) | Alembic migration: 0031 workforce leave. |
| [backend/migrations/versions/0032_workforce_payroll.py](backend/migrations/versions/0032_workforce_payroll.py) | Alembic migration: 0032 workforce payroll. |
| [backend/migrations/versions/0033_workforce_payroll_unpaid_leave_deduction.py](backend/migrations/versions/0033_workforce_payroll_unpaid_leave_deduction.py) | Alembic migration: 0033 workforce payroll unpaid leave deduction. |
| [backend/migrations/versions/0034_workforce_announcements.py](backend/migrations/versions/0034_workforce_announcements.py) | Alembic migration: 0034 workforce announcements. |
| [backend/migrations/versions/0035_workforce_announcements_phase5.py](backend/migrations/versions/0035_workforce_announcements_phase5.py) | Alembic migration: 0035 workforce announcements phase5. |
| [backend/migrations/versions/0036_workforce_announcement_automation_dedupe.py](backend/migrations/versions/0036_workforce_announcement_automation_dedupe.py) | Alembic migration: 0036 workforce announcement automation dedupe. |
| [backend/migrations/versions/0037_workforce_hr_admin_phase6.py](backend/migrations/versions/0037_workforce_hr_admin_phase6.py) | Alembic migration: 0037 workforce hr admin phase6. |
| [backend/migrations/versions/0038_workforce_policy_ack_updated_at_default.py](backend/migrations/versions/0038_workforce_policy_ack_updated_at_default.py) | Alembic migration: 0038 workforce policy ack updated at default. |
| [backend/migrations/versions/0039_org_settings_workforce_canonical_flag.py](backend/migrations/versions/0039_org_settings_workforce_canonical_flag.py) | Alembic migration: 0039 org settings workforce canonical flag. |
| [backend/migrations/versions/0040_auth_confirmation_code_and_provider_settings.py](backend/migrations/versions/0040_auth_confirmation_code_and_provider_settings.py) | Alembic migration: 0040 auth confirmation code and provider settings. |
| [backend/pyproject.toml](backend/pyproject.toml) | Python packaging/dependencies/format/lint/pytest configuration. |
| [backend/scripts/migration_safety_check.py](backend/scripts/migration_safety_check.py) | Python backend/operational/runtime/load tool: migration safety check. |

#### bridge files

| File | Responsibility |
| --- | --- |
| [bridge/base/0-ai-coo-namespace.yaml](bridge/base/0-ai-coo-namespace.yaml) | Generated Kubernetes 0 ai coo namespace resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/backend-deployment.yaml](bridge/base/backend-deployment.yaml) | Generated Kubernetes backend deployment resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/backend-expose.yaml](bridge/base/backend-expose.yaml) | Generated Kubernetes backend expose resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/backend-service.yaml](bridge/base/backend-service.yaml) | Generated Kubernetes backend service resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/beat-deployment.yaml](bridge/base/beat-deployment.yaml) | Generated Kubernetes beat deployment resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/default-network-policy.yaml](bridge/base/default-network-policy.yaml) | Generated Kubernetes default network policy resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/frontend-deployment.yaml](bridge/base/frontend-deployment.yaml) | Generated Kubernetes frontend deployment resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/frontend-expose.yaml](bridge/base/frontend-expose.yaml) | Generated Kubernetes frontend expose resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/frontend-service.yaml](bridge/base/frontend-service.yaml) | Generated Kubernetes frontend service resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/kustomization.yaml](bridge/base/kustomization.yaml) | Generated Kubernetes kustomization resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/minio-deployment.yaml](bridge/base/minio-deployment.yaml) | Generated Kubernetes minio deployment resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/minio-expose.yaml](bridge/base/minio-expose.yaml) | Generated Kubernetes minio expose resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/minio-miniodata-persistentVolumeClaim.yaml](bridge/base/minio-miniodata-persistentVolumeClaim.yaml) | Generated Kubernetes minio miniodata persistentVolumeClaim resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/minio-service.yaml](bridge/base/minio-service.yaml) | Generated Kubernetes minio service resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/postgres-deployment.yaml](bridge/base/postgres-deployment.yaml) | Generated Kubernetes postgres deployment resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/postgres-expose.yaml](bridge/base/postgres-expose.yaml) | Generated Kubernetes postgres expose resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/postgres-pgdata-persistentVolumeClaim.yaml](bridge/base/postgres-pgdata-persistentVolumeClaim.yaml) | Generated Kubernetes postgres pgdata persistentVolumeClaim resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/postgres-service.yaml](bridge/base/postgres-service.yaml) | Generated Kubernetes postgres service resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/redis-deployment.yaml](bridge/base/redis-deployment.yaml) | Generated Kubernetes redis deployment resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/redis-expose.yaml](bridge/base/redis-expose.yaml) | Generated Kubernetes redis expose resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/redis-service.yaml](bridge/base/redis-service.yaml) | Generated Kubernetes redis service resource. Review development values, credentials and deployment assumptions. |
| [bridge/base/worker-deployment.yaml](bridge/base/worker-deployment.yaml) | Generated Kubernetes worker deployment resource. Review development values, credentials and deployment assumptions. |
| [bridge/overlays/desktop/backend-service.yaml](bridge/overlays/desktop/backend-service.yaml) | Generated Kubernetes backend service resource. Review development values, credentials and deployment assumptions. |
| [bridge/overlays/desktop/frontend-service.yaml](bridge/overlays/desktop/frontend-service.yaml) | Generated Kubernetes frontend service resource. Review development values, credentials and deployment assumptions. |
| [bridge/overlays/desktop/kustomization.yaml](bridge/overlays/desktop/kustomization.yaml) | Generated Kubernetes kustomization resource. Review development values, credentials and deployment assumptions. |
| [bridge/overlays/desktop/minio-miniodata-persistentVolumeClaim.yaml](bridge/overlays/desktop/minio-miniodata-persistentVolumeClaim.yaml) | Generated Kubernetes minio miniodata persistentVolumeClaim resource. Review development values, credentials and deployment assumptions. |
| [bridge/overlays/desktop/minio-service.yaml](bridge/overlays/desktop/minio-service.yaml) | Generated Kubernetes minio service resource. Review development values, credentials and deployment assumptions. |
| [bridge/overlays/desktop/postgres-pgdata-persistentVolumeClaim.yaml](bridge/overlays/desktop/postgres-pgdata-persistentVolumeClaim.yaml) | Generated Kubernetes postgres pgdata persistentVolumeClaim resource. Review development values, credentials and deployment assumptions. |
| [bridge/overlays/desktop/postgres-service.yaml](bridge/overlays/desktop/postgres-service.yaml) | Generated Kubernetes postgres service resource. Review development values, credentials and deployment assumptions. |
| [bridge/overlays/desktop/redis-service.yaml](bridge/overlays/desktop/redis-service.yaml) | Generated Kubernetes redis service resource. Review development values, credentials and deployment assumptions. |

#### docker files

| File | Responsibility |
| --- | --- |
| [docker/minio/README.md](docker/minio/README.md) | Infrastructure notes/reference configuration for minio. |
| [docker/nginx/README.md](docker/nginx/README.md) | Infrastructure notes/reference configuration for nginx. |
| [docker/nginx/default.conf](docker/nginx/default.conf) | Infrastructure notes/reference configuration for nginx. |
| [docker/postgres/README.md](docker/postgres/README.md) | Infrastructure notes/reference configuration for postgres. |
| [docker/redis/README.md](docker/redis/README.md) | Infrastructure notes/reference configuration for redis. |

#### docs files

| File | Responsibility |
| --- | --- |
| [docs/PHASE6_PRODUCT_COMPLETION.md](docs/PHASE6_PRODUCT_COMPLETION.md) | Phase 6 — Verification & product completion report. Sections: 1. Complete remaining-work audit; 2. Implementation changelog (route / module); 3. Verification report; 3.1 Commands executed (2026-04-09); 3.1.1 Runtime verification (2026-04-10); 3.2 Playwright smoke (local); 3.3 Code inspection; 3.4 Not run in this pass; 4. Final completion matrix; 5. Remaining known gaps; 6. Final product status; Follow-up implementation (post–Phase 6). Historical/current guidance or proposals; compare with source. |
| [docs/RBAC_MATRIX.md](docs/RBAC_MATRIX.md) | RBAC matrix (product surfaces). Sections: Auth transport notes; Verification. Historical/current guidance or proposals; compare with source. |
| [docs/WORKFORCE_PHASE0_ARCHITECTURE.md](docs/WORKFORCE_PHASE0_ARCHITECTURE.md) | Workforce — Phase 0 (Foundation audit + architecture). Sections: 1) Backend module plan (where Workforce lives); Phase 6–7 backend (implemented); 2) Frontend route/folder plan; Phase 6–7 frontend (implemented); 3) Entity/data model plan (canonical); Already present (Phases 1–5); Phase 6 entity scope (HR admin); Phase 7 intelligence scope (no new event store); 4) RBAC / permission plan; Manager relationships; 5) Phased implementation plan (files + verification strategy); Phase 8 verification (responsive + state); Workforce runtime smoke (Phase 7 intelligence); 6) Prerequisite refactors / infra notes (before Phase 1 verification). Historical/current guidance or proposals; compare with source. |
| [docs/epic_a_closure_delta.md](docs/epic_a_closure_delta.md) | Epic A Closure Delta (Plaid Integration). Sections: Scope; Regression Verification (Rebuilt Containers); API Evidence; Service/Worker Evidence; Frontend UX Evidence; Test Evidence; Playwright Pass/Skip Matrix (Latest Full Run); Residual Risks. Historical/current guidance or proposals; compare with source. |
| [docs/epic_b_closure_delta.md](docs/epic_b_closure_delta.md) | Epic B Closure Delta (Stripe Integration and Reconciliation). Sections: Scope; API Evidence; Service Evidence; Frontend Evidence; Test Evidence; CI Evidence; Residual Risks. Historical/current guidance or proposals; compare with source. |
| [docs/epic_c_closure_delta.md](docs/epic_c_closure_delta.md) | Epic C Closure Delta (Budgets + Alert Freshness Signal). Sections: Scope; Backend Evidence; Frontend Evidence; Test Evidence; Regression Verification (This Run); Residual Risks. Historical/current guidance or proposals; compare with source. |
| [docs/epic_d_closure_delta.md](docs/epic_d_closure_delta.md) | Epic D Closure Delta (Multi-Location Analytics). Sections: Scope; API Evidence; Domain/Storage Evidence; Frontend Evidence; Test Evidence; Closure Status. Historical/current guidance or proposals; compare with source. |
| [docs/epic_d_location_delta.md](docs/epic_d_location_delta.md) | Epic D Location Delta. Sections: Scope completed; Key files; Tests added/updated. Historical/current guidance or proposals; compare with source. |
| [docs/epic_e_inventory_delta.md](docs/epic_e_inventory_delta.md) | Epic E Closure Delta (Inventory Forecasting). Sections: Scope Added In This Slice; Evidence; Tests; Verification; Perf Gate Closure; Status. Historical/current guidance or proposals; compare with source. |
| [docs/epic_f_backend_delta.md](docs/epic_f_backend_delta.md) | Epic F Delta (AI Chat Assistant). Sections: Scope Delivered; Evidence; Verification; Remaining For Full Epic F Closure. Historical/current guidance or proposals; compare with source. |
| [docs/final_cross_epic_closure_matrix.md](docs/final_cross_epic_closure_matrix.md) | Final Cross-Epic Closure Matrix (Stage-2 A-F). Sections: Overall verdict; Matrix; Cross-epic regression status; Remaining non-blocking hardening. Historical/current guidance or proposals; compare with source. |
| [docs/final_cross_epic_verification_appendix.md](docs/final_cross_epic_verification_appendix.md) | Final Cross-Epic Verification Appendix. Sections: 1) Backend full regression; 2) Frontend production build; 3) Full Playwright run (latest); Spec matrix; 4) Perf gate and load artifacts; Gate summary; Key guardrail metrics; Additional high-churn observations (non-gating). Historical/current guidance or proposals; compare with source. |
| [docs/final_srs_delta_matrix.md](docs/final_srs_delta_matrix.md) | Final SRS Delta Matrix (Current Snapshot). Sections: Stage-2 epic completion rollup. Historical/current guidance or proposals; compare with source. |
| [docs/frontend_complete_improvement_plan.md](docs/frontend_complete_improvement_plan.md) | Frontend Complete Improvement Plan (Functional + UX). Sections: Audit Evidence; Functional Status Matrix (Frontend); Is Frontend “Completely Working”?; UX Flow Findings (First-Time User Perspective); Strengths; Friction Points; Complete Improvement Plan; P0 (Immediate: 1-2 sprints); P1 (Near-term: 2-4 sprints); P2 (Next-level polish: 4-8 sprints); Page-by-Page Implementation Backlog; Execution Order Recommendation; P0 Implementation Delta (2026-03-27); Full Playwright Pass/Fail Matrix (Rebuilt Stack); Env-Gated CI Lane Validation. Historical/current guidance or proposals; compare with source. |
| [docs/frontend_current_state_handover.md](docs/frontend_current_state_handover.md) | frontend current state handover. Historical/current guidance or proposals; compare with source. |
| [docs/frontend_redesign_release_prep.md](docs/frontend_redesign_release_prep.md) | Frontend Redesign Release Prep. Sections: Scope; Selector Cleanup; Verification Results; Exact Touched Files (Release Bundle); Risk Notes. Historical/current guidance or proposals; compare with source. |
| [docs/frontend_redesign_remaining_checklist.md](docs/frontend_redesign_remaining_checklist.md) | Frontend Redesign Remaining Checklist (Strict). Sections: Completion Rules (Strict); Wave R1 - Shared Contract Gaps (Component Inventory Parity); Wave R2 - Dashboard Remaining Gaps; Wave R3 - Transactions Premium Workflow Completion; Wave R4 - Alerts and Reports Remaining Premium Gaps; Wave R5 - Remaining Route Depth (Budgets, Forecast, Inventory, Assistant, Onboarding, Orgs); Wave R6 - Global State and Accessibility/Animation Hardening; Wave R7 - Tests and Selector Policy Completion; Final Sign-off Checklist. Historical/current guidance or proposals; compare with source. |
| [docs/operations/ai_live_mode.md](docs/operations/ai_live_mode.md) | AI Live Mode Verification. Sections: 1) Set env values; Option A: OpenAI; Option B: Office Ollama server (shared API); 2) Verify provider health; 3) Verify grounded summary + fallback behavior. Historical/current guidance or proposals; compare with source. |
| [docs/operations/backup_restore.md](docs/operations/backup_restore.md) | Backup and Restore (Postgres + MinIO). Sections: Targets; Postgres backup; Postgres restore; MinIO backup (reports bucket); MinIO restore; Suggested schedule; Scripted commands in this repo. Historical/current guidance or proposals; compare with source. |
| [docs/operations/ci_env_gated_lanes.md](docs/operations/ci_env_gated_lanes.md) | CI Env-Gated Lanes. Sections: Variables; Required secrets by lane; Plaid lane; AI live lane; Manual workflow_dispatch switches; Release usage. Historical/current guidance or proposals; compare with source. |
| [docs/operations/owner_admin_runbook.md](docs/operations/owner_admin_runbook.md) | Owner/Admin Operations Runbook. Sections: Scope; Frontend auth/network behavior; Owner diagnostics panel (Activity); DLQ triage procedure; Outbox retry procedure; Queue lag / worker health procedure; Security/compliance procedures; Post-incident verification; Alert freshness triggers (budget/import writes). Historical/current guidance or proposals; compare with source. |
| [docs/operations/privacy_deletion.md](docs/operations/privacy_deletion.md) | Privacy and Deletion Operations. Sections: Owner UI controls; Deletion lifecycle; CI migration safety gate. Historical/current guidance or proposals; compare with source. |
| [docs/operations/release_checklist.md](docs/operations/release_checklist.md) | Release Checklist (Strict Go/No-Go). Sections: 1. Pre-Release Preconditions; 2. Security and Secret Hygiene; 3. CI Gate Matrix (Must Be Green); 4. Database and Migration Safety; 5. AI Live-Mode Readiness (When Enabled); 6. Performance and Scalability Gates; 7. Operational Readiness; 8. Deployment Execution; 9. Post-Deploy Verification; 10. Rollback Criteria and Trigger; 11. Final Sign-Off. Historical/current guidance or proposals; compare with source. |
| [docs/operations/secret_hygiene_checklist.md](docs/operations/secret_hygiene_checklist.md) | Secret Hygiene Checklist. Sections: 1) Repository hygiene; 2) Secret injection policy; 3) Required production secrets; 4) Rotation cadence; 5) Incident response for key exposure; 6) Release gate. Historical/current guidance or proposals; compare with source. |
| [docs/operations/worker_resilience.md](docs/operations/worker_resilience.md) | Worker Resilience and DLQ Operations. Sections: Scope; Signals; Dead-letter API; Operator Flow. Historical/current guidance or proposals; compare with source. |
| [docs/performance.md](docs/performance.md) | Performance Harness. Sections: Goals; Seed dataset; Bootstrap auth/org; k6 profiles; 1) CI smoke profile; 2) Many-org dashboard reads; 3) Report burst generation; 4) Mixed churn profile; 5) Read-only hotpaths profile; 6) Write-heavy profile; 7) Runtime observability profile (out-of-band); 8) Inventory churn profile (Epic E); 9) Perf gate evaluator; Local scalability runbook; Performance expectations and limits; Operational hardening notes; CI workflow; Runtime SLO telemetry. Historical/current guidance or proposals; compare with source. |
| [docs/srs_traceability_stage1_p1_delta.md](docs/srs_traceability_stage1_p1_delta.md) | Stage-1 P1 Traceability Delta. Sections: Status matrix (requested items); Completed in this change set; Operational resilience depth; Queue lag / worker health alerting extension; Owner/admin diagnostics UX; Frontend global error UX consistency pass; Runbook expansion; Epic-C delta: alert refresh queue feedback and visibility; Stage-1 P0 closure update: brute-force lockout escalation telemetry/audit; Validation evidence; Playwright full-suite matrix (2026-03-25). Historical/current guidance or proposals; compare with source. |
| [docs/workforce_final_audit_report.md](docs/workforce_final_audit_report.md) | Workforce Final Audit Report (Strict Gate). Sections: 1) Workforce Completion Matrix; 2) End-to-End Flow Status; 3) Security/RBAC Findings; 4) Responsive Findings; 5) Test Coverage Findings; 6) P0/P1/P2 Fix List; 7) Final Verdict. Historical/current guidance or proposals; compare with source. |

#### frontend files

| File | Responsibility |
| --- | --- |
| [frontend/.env.e2e.local](frontend/.env.e2e.local) | Configuration/generated contract/support artifact: .env.e2e.local. |
| [frontend/.eslintrc.json](frontend/.eslintrc.json) | Configuration/generated contract/support artifact: .eslintrc.json. |
| [frontend/.tmp-next-3001.pid](frontend/.tmp-next-3001.pid) | Tracked local runtime/debug helper or log/PID artifact; not application source. |
| [frontend/.tmp-next-3002.pid](frontend/.tmp-next-3002.pid) | Tracked local runtime/debug helper or log/PID artifact; not application source. |
| [frontend/Dockerfile](frontend/Dockerfile) | Container build/entrypoint for frontend. |
| [frontend/README.md](frontend/README.md) | AI COO Frontend. Sections: Stack; Routes; Environment variables; Auth mode notes; Chart and UX notes; Development; Quality commands; Performance notes; E2E notes; What runs today; Shared auth fixture; Base URL and managed server (important); Recommended local command (managed frontend); Other E2E env; Architecture rules; Graceful UI fallbacks. Historical/current guidance or proposals; compare with source. |
| [frontend/e2e/ai-chat.spec.ts](frontend/e2e/ai-chat.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/alert-refresh-queue.spec.ts](frontend/e2e/alert-refresh-queue.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/alerts-actions.spec.ts](frontend/e2e/alerts-actions.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/auth-confirm-ui.spec.ts](frontend/e2e/auth-confirm-ui.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/budgets.spec.ts](frontend/e2e/budgets.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/cookie-csrf.spec.ts](frontend/e2e/cookie-csrf.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/dashboard-budget-variance.spec.ts](frontend/e2e/dashboard-budget-variance.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/fixtures/auth.ts](frontend/e2e/fixtures/auth.ts) | Playwright test/fixture/setup. Exports: E2eAuthSessionSlice, e2eAuthenticatedPost, e2eAuthenticatedGet, test. |
| [frontend/e2e/full-flow.spec.ts](frontend/e2e/full-flow.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/global-setup.ts](frontend/e2e/global-setup.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/imports-workflow.spec.ts](frontend/e2e/imports-workflow.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/inventory-alerts.spec.ts](frontend/e2e/inventory-alerts.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/mfa-session.spec.ts](frontend/e2e/mfa-session.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/onboarding-workspace.spec.ts](frontend/e2e/onboarding-workspace.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/ops-flow.spec.ts](frontend/e2e/ops-flow.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/plaid-integration.spec.ts](frontend/e2e/plaid-integration.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/polish.spec.ts](frontend/e2e/polish.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/rbac-viewer-api.spec.ts](frontend/e2e/rbac-viewer-api.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/rbac-viewer-settings-api.spec.ts](frontend/e2e/rbac-viewer-settings-api.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/reports-workflow.spec.ts](frontend/e2e/reports-workflow.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/responsive-mobile.spec.ts](frontend/e2e/responsive-mobile.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/responsive-smoke.spec.ts](frontend/e2e/responsive-smoke.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/sse-fallback.spec.ts](frontend/e2e/sse-fallback.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/stripe-integration.spec.ts](frontend/e2e/stripe-integration.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/stripe-reconciliation-invalid-range.spec.ts](frontend/e2e/stripe-reconciliation-invalid-range.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/transactions-workflow.spec.ts](frontend/e2e/transactions-workflow.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/visual.spec.ts](frontend/e2e/visual.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-activity-failure-retry.spec.ts](frontend/e2e/workforce-activity-failure-retry.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-attendance.spec.ts](frontend/e2e/workforce-attendance.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-communications-failure-states.spec.ts](frontend/e2e/workforce-communications-failure-states.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-hr-admin.spec.ts](frontend/e2e/workforce-hr-admin.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-leave-workflow.spec.ts](frontend/e2e/workforce-leave-workflow.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-leave.spec.ts](frontend/e2e/workforce-leave.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-mobile-dense-interactions.spec.ts](frontend/e2e/workforce-mobile-dense-interactions.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-onboarding-offboarding.spec.ts](frontend/e2e/workforce-onboarding-offboarding.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-payroll-workflow.spec.ts](frontend/e2e/workforce-payroll-workflow.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-payroll.spec.ts](frontend/e2e/workforce-payroll.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-phase1.spec.ts](frontend/e2e/workforce-phase1.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-phase7-intelligence.spec.ts](frontend/e2e/workforce-phase7-intelligence.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-rbac-negative.spec.ts](frontend/e2e/workforce-rbac-negative.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-responsive.spec.ts](frontend/e2e/workforce-responsive.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/e2e/workforce-state-matrix.spec.ts](frontend/e2e/workforce-state-matrix.spec.ts) | Playwright test/fixture/setup. See source declarations. |
| [frontend/next-3000-e2e.log](frontend/next-3000-e2e.log) | Tracked local runtime/debug helper or log/PID artifact; not application source. |
| [frontend/next-3000-live.log](frontend/next-3000-live.log) | Tracked local runtime/debug helper or log/PID artifact; not application source. |
| [frontend/next-3001-e2e.log](frontend/next-3001-e2e.log) | Tracked local runtime/debug helper or log/PID artifact; not application source. |
| [frontend/next-3001.log](frontend/next-3001.log) | Tracked local runtime/debug helper or log/PID artifact; not application source. |
| [frontend/next-env.d.ts](frontend/next-env.d.ts) | Frontend/shared configuration or type module. See source declarations. |
| [frontend/next.config.js](frontend/next.config.js) | Frontend/shared configuration or type module. See source declarations. |
| [frontend/package-lock.json](frontend/package-lock.json) | Resolved npm dependency/integrity lockfile. |
| [frontend/package.json](frontend/package.json) | Frontend npm commands/runtime/development dependency declarations. |
| [frontend/playwright-report-full.json](frontend/playwright-report-full.json) | Configuration/generated contract/support artifact: playwright-report-full.json. |
| [frontend/playwright.config.ts](frontend/playwright.config.ts) | Frontend/shared configuration or type module. See source declarations. |
| [frontend/postcss.config.js](frontend/postcss.config.js) | Frontend/shared configuration or type module. See source declarations. |
| [frontend/src/app/(auth)/confirm/page.tsx](<frontend/src/app/(auth)/confirm/page.tsx>) | App Router page/layout/error/loading/alias for (auth)/confirm. See source declarations. |
| [frontend/src/app/(auth)/login/page.tsx](<frontend/src/app/(auth)/login/page.tsx>) | App Router page/layout/error/loading/alias for (auth)/login. See source declarations. |
| [frontend/src/app/(auth)/register/page.tsx](<frontend/src/app/(auth)/register/page.tsx>) | App Router page/layout/error/loading/alias for (auth)/register. See source declarations. |
| [frontend/src/app/activity/page.tsx](frontend/src/app/activity/page.tsx) | App Router page/layout/error/loading/alias for activity. See source declarations. |
| [frontend/src/app/admin-console/page.tsx](frontend/src/app/admin-console/page.tsx) | App Router page/layout/error/loading/alias for admin-console. See source declarations. |
| [frontend/src/app/app/activity/page.tsx](frontend/src/app/app/activity/page.tsx) | App Router page/layout/error/loading/alias for app/activity. See source declarations. |
| [frontend/src/app/app/admin-console/page.tsx](frontend/src/app/app/admin-console/page.tsx) | App Router page/layout/error/loading/alias for app/admin-console. See source declarations. |
| [frontend/src/app/app/alerts/page.tsx](frontend/src/app/app/alerts/page.tsx) | App Router page/layout/error/loading/alias for app/alerts. See source declarations. |
| [frontend/src/app/app/assistant/page.tsx](frontend/src/app/app/assistant/page.tsx) | App Router page/layout/error/loading/alias for app/assistant. See source declarations. |
| [frontend/src/app/app/budgets/page.tsx](frontend/src/app/app/budgets/page.tsx) | App Router page/layout/error/loading/alias for app/budgets. See source declarations. |
| [frontend/src/app/app/dashboard/page.tsx](frontend/src/app/app/dashboard/page.tsx) | App Router page/layout/error/loading/alias for app/dashboard. See source declarations. |
| [frontend/src/app/app/error.tsx](frontend/src/app/app/error.tsx) | App Router page/layout/error/loading/alias for app. See source declarations. |
| [frontend/src/app/app/forecast/page.tsx](frontend/src/app/app/forecast/page.tsx) | App Router page/layout/error/loading/alias for app/forecast. See source declarations. |
| [frontend/src/app/app/inventory/page.tsx](frontend/src/app/app/inventory/page.tsx) | App Router page/layout/error/loading/alias for app/inventory. See source declarations. |
| [frontend/src/app/app/layout.tsx](frontend/src/app/app/layout.tsx) | App Router page/layout/error/loading/alias for app. See source declarations. |
| [frontend/src/app/app/loading.tsx](frontend/src/app/app/loading.tsx) | App Router page/layout/error/loading/alias for app. See source declarations. |
| [frontend/src/app/app/onboarding/page.tsx](frontend/src/app/app/onboarding/page.tsx) | App Router page/layout/error/loading/alias for app/onboarding. See source declarations. |
| [frontend/src/app/app/orgs/page.tsx](frontend/src/app/app/orgs/page.tsx) | App Router page/layout/error/loading/alias for app/orgs. See source declarations. |
| [frontend/src/app/app/page.tsx](frontend/src/app/app/page.tsx) | App Router page/layout/error/loading/alias for app. See source declarations. |
| [frontend/src/app/app/reports/page.tsx](frontend/src/app/app/reports/page.tsx) | App Router page/layout/error/loading/alias for app/reports. See source declarations. |
| [frontend/src/app/app/settings/page.tsx](frontend/src/app/app/settings/page.tsx) | App Router page/layout/error/loading/alias for app/settings. See source declarations. |
| [frontend/src/app/app/transactions/page.tsx](frontend/src/app/app/transactions/page.tsx) | App Router page/layout/error/loading/alias for app/transactions. See source declarations. |
| [frontend/src/app/app/workforce/attendance/page.tsx](frontend/src/app/app/workforce/attendance/page.tsx) | App Router page/layout/error/loading/alias for app/workforce/attendance. See source declarations. |
| [frontend/src/app/app/workforce/communications/page.tsx](frontend/src/app/app/workforce/communications/page.tsx) | App Router page/layout/error/loading/alias for app/workforce/communications. See source declarations. |
| [frontend/src/app/app/workforce/communications/templates/page.tsx](frontend/src/app/app/workforce/communications/templates/page.tsx) | App Router page/layout/error/loading/alias for app/workforce/communications/templates. See source declarations. |
| [frontend/src/app/app/workforce/employees/[employeeId]/page.tsx](<frontend/src/app/app/workforce/employees/[employeeId]/page.tsx>) | App Router page/layout/error/loading/alias for app/workforce/employees/[employeeId]. See source declarations. |
| [frontend/src/app/app/workforce/employees/page.tsx](frontend/src/app/app/workforce/employees/page.tsx) | App Router page/layout/error/loading/alias for app/workforce/employees. See source declarations. |
| [frontend/src/app/app/workforce/hr/page.tsx](frontend/src/app/app/workforce/hr/page.tsx) | App Router page/layout/error/loading/alias for app/workforce/hr. See source declarations. |
| [frontend/src/app/app/workforce/leave/page.tsx](frontend/src/app/app/workforce/leave/page.tsx) | App Router page/layout/error/loading/alias for app/workforce/leave. See source declarations. |
| [frontend/src/app/app/workforce/page.tsx](frontend/src/app/app/workforce/page.tsx) | App Router page/layout/error/loading/alias for app/workforce. See source declarations. |
| [frontend/src/app/app/workforce/payroll/page.tsx](frontend/src/app/app/workforce/payroll/page.tsx) | App Router page/layout/error/loading/alias for app/workforce/payroll. See source declarations. |
| [frontend/src/app/auth/confirm/page.tsx](frontend/src/app/auth/confirm/page.tsx) | App Router page/layout/error/loading/alias for auth/confirm. See source declarations. |
| [frontend/src/app/auth/login/page.tsx](frontend/src/app/auth/login/page.tsx) | App Router page/layout/error/loading/alias for auth/login. See source declarations. |
| [frontend/src/app/auth/register/page.tsx](frontend/src/app/auth/register/page.tsx) | App Router page/layout/error/loading/alias for auth/register. See source declarations. |
| [frontend/src/app/budgets/page.tsx](frontend/src/app/budgets/page.tsx) | App Router page/layout/error/loading/alias for budgets. See source declarations. |
| [frontend/src/app/dashboard/page.tsx](frontend/src/app/dashboard/page.tsx) | App Router page/layout/error/loading/alias for dashboard. See source declarations. |
| [frontend/src/app/error.tsx](frontend/src/app/error.tsx) | App Router page/layout/error/loading/alias for error.tsx. See source declarations. |
| [frontend/src/app/favicon.ico](frontend/src/app/favicon.ico) | Application icon/favicon or historical visual-test artifact. |
| [frontend/src/app/forecast/page.tsx](frontend/src/app/forecast/page.tsx) | App Router page/layout/error/loading/alias for forecast. See source declarations. |
| [frontend/src/app/globals.css](frontend/src/app/globals.css) | Global/UI design tokens, themes and layout styling. |
| [frontend/src/app/icon.png](frontend/src/app/icon.png) | Application icon/favicon or historical visual-test artifact. |
| [frontend/src/app/layout.tsx](frontend/src/app/layout.tsx) | App Router page/layout/error/loading/alias for layout.tsx. Exports: metadata. |
| [frontend/src/app/onboarding/page.tsx](frontend/src/app/onboarding/page.tsx) | App Router page/layout/error/loading/alias for onboarding. See source declarations. |
| [frontend/src/app/page.tsx](frontend/src/app/page.tsx) | App Router page/layout/error/loading/alias for page.tsx. See source declarations. |
| [frontend/src/app/reports/page.tsx](frontend/src/app/reports/page.tsx) | App Router page/layout/error/loading/alias for reports. See source declarations. |
| [frontend/src/app/settings/page.tsx](frontend/src/app/settings/page.tsx) | App Router page/layout/error/loading/alias for settings. See source declarations. |
| [frontend/src/app/transactions/page.tsx](frontend/src/app/transactions/page.tsx) | App Router page/layout/error/loading/alias for transactions. See source declarations. |
| [frontend/src/components/activity/admin-status-panel.tsx](frontend/src/components/activity/admin-status-panel.tsx) | UI/data-surface/shell/chart component (admin status panel). Exports: AdminStatusPanel. |
| [frontend/src/components/activity/operations-health-card.tsx](frontend/src/components/activity/operations-health-card.tsx) | UI/data-surface/shell/chart component (operations health card). Exports: OperationsHealthCard. |
| [frontend/src/components/ai/ai-brief-card.tsx](frontend/src/components/ai/ai-brief-card.tsx) | UI/data-surface/shell/chart component (ai brief card). Exports: AiBriefCard. |
| [frontend/src/components/ai/prompt-suggestions.tsx](frontend/src/components/ai/prompt-suggestions.tsx) | UI/data-surface/shell/chart component (prompt suggestions). Exports: PromptSuggestions. |
| [frontend/src/components/alerts/alert-detail-card.tsx](frontend/src/components/alerts/alert-detail-card.tsx) | UI/data-surface/shell/chart component (alert detail card). Exports: AlertDetailCard. |
| [frontend/src/components/alerts/alert-list.tsx](frontend/src/components/alerts/alert-list.tsx) | UI/data-surface/shell/chart component (alert list). Exports: AlertList. |
| [frontend/src/components/charts/chart-canvas.tsx](frontend/src/components/charts/chart-canvas.tsx) | UI/data-surface/shell/chart component (chart canvas). Exports: ChartCanvas. |
| [frontend/src/components/charts/chart-card.tsx](frontend/src/components/charts/chart-card.tsx) | UI/data-surface/shell/chart component (chart card). Exports: ChartCard. |
| [frontend/src/components/charts/chart-frame.tsx](frontend/src/components/charts/chart-frame.tsx) | UI/data-surface/shell/chart component (chart frame). Exports: ChartFrame. |
| [frontend/src/components/charts/chart-tooltip.tsx](frontend/src/components/charts/chart-tooltip.tsx) | UI/data-surface/shell/chart component (chart tooltip). Exports: FinancialTooltip. |
| [frontend/src/components/charts/sparkline.tsx](frontend/src/components/charts/sparkline.tsx) | UI/data-surface/shell/chart component (sparkline). Exports: Sparkline. |
| [frontend/src/components/charts/theme.ts](frontend/src/components/charts/theme.ts) | UI/data-surface/shell/chart component (theme). Exports: chartPalette. |
| [frontend/src/components/common/action-card.tsx](frontend/src/components/common/action-card.tsx) | UI/data-surface/shell/chart component (action card). Exports: ActionCard. |
| [frontend/src/components/common/ai-insight-panel.tsx](frontend/src/components/common/ai-insight-panel.tsx) | UI/data-surface/shell/chart component (ai insight panel). Exports: AIInsightPanel. |
| [frontend/src/components/common/alert-card.tsx](frontend/src/components/common/alert-card.tsx) | UI/data-surface/shell/chart component (alert card). Exports: AlertCard. |
| [frontend/src/components/common/empty-state.tsx](frontend/src/components/common/empty-state.tsx) | UI/data-surface/shell/chart component (empty state). Exports: EmptyState. |
| [frontend/src/components/common/error-state.tsx](frontend/src/components/common/error-state.tsx) | UI/data-surface/shell/chart component (error state). Exports: ErrorState. |
| [frontend/src/components/common/experience-tier-gate.tsx](frontend/src/components/common/experience-tier-gate.tsx) | UI/data-surface/shell/chart component (experience tier gate). Exports: ExperienceTierGate. |
| [frontend/src/components/common/filters-bar.tsx](frontend/src/components/common/filters-bar.tsx) | UI/data-surface/shell/chart component (filters bar). Exports: TxFilters, FiltersBar. |
| [frontend/src/components/common/global-api-feedback.tsx](frontend/src/components/common/global-api-feedback.tsx) | UI/data-surface/shell/chart component (global api feedback). Exports: GlobalApiFeedback. |
| [frontend/src/components/common/insight-card.tsx](frontend/src/components/common/insight-card.tsx) | UI/data-surface/shell/chart component (insight card). Exports: InsightCard. |
| [frontend/src/components/common/progress-card.tsx](frontend/src/components/common/progress-card.tsx) | UI/data-surface/shell/chart component (progress card). Exports: ProgressCard. |
| [frontend/src/components/common/progressive-disclosure.tsx](frontend/src/components/common/progressive-disclosure.tsx) | UI/data-surface/shell/chart component (progressive disclosure). Exports: ProgressiveDisclosure. |
| [frontend/src/components/common/providers.tsx](frontend/src/components/common/providers.tsx) | UI/data-surface/shell/chart component (providers). Exports: Providers. |
| [frontend/src/components/common/section-header.tsx](frontend/src/components/common/section-header.tsx) | UI/data-surface/shell/chart component (section header). Exports: SectionHeader. |
| [frontend/src/components/common/theme-toggle.tsx](frontend/src/components/common/theme-toggle.tsx) | UI/data-surface/shell/chart component (theme toggle). Exports: ThemeToggle. |
| [frontend/src/components/common/toaster.tsx](frontend/src/components/common/toaster.tsx) | UI/data-surface/shell/chart component (toaster). Exports: Toaster. |
| [frontend/src/components/common/use-toast.ts](frontend/src/components/common/use-toast.ts) | UI/data-surface/shell/chart component (use toast). Exports: ToastVariant, Toast, useToastStore, useToast. |
| [frontend/src/components/data-surface/advanced-filters-panel.tsx](frontend/src/components/data-surface/advanced-filters-panel.tsx) | UI/data-surface/shell/chart component (advanced filters panel). Exports: AdvancedFiltersPanel. |
| [frontend/src/components/data-surface/bulk-action-bar.tsx](frontend/src/components/data-surface/bulk-action-bar.tsx) | UI/data-surface/shell/chart component (bulk action bar). Exports: BulkActionBar. |
| [frontend/src/components/data-surface/column-visibility-menu.tsx](frontend/src/components/data-surface/column-visibility-menu.tsx) | UI/data-surface/shell/chart component (column visibility menu). Exports: ColumnVisibilityMenu. |
| [frontend/src/components/data-surface/row-action-menu.tsx](frontend/src/components/data-surface/row-action-menu.tsx) | UI/data-surface/shell/chart component (row action menu). Exports: RowActionMenu. |
| [frontend/src/components/data-surface/saved-view-selector.tsx](frontend/src/components/data-surface/saved-view-selector.tsx) | UI/data-surface/shell/chart component (saved view selector). Exports: SavedViewSelector. |
| [frontend/src/components/data-surface/simple-data-table.tsx](frontend/src/components/data-surface/simple-data-table.tsx) | UI/data-surface/shell/chart component (simple data table). Exports: SimpleDataTable. |
| [frontend/src/components/data-surface/smart-data-table.tsx](frontend/src/components/data-surface/smart-data-table.tsx) | UI/data-surface/shell/chart component (smart data table). Exports: SmartDataTable. |
| [frontend/src/components/data-surface/table-toolbar.tsx](frontend/src/components/data-surface/table-toolbar.tsx) | UI/data-surface/shell/chart component (table toolbar). Exports: TableToolbar. |
| [frontend/src/components/data-surface/virtualized-grid.tsx](frontend/src/components/data-surface/virtualized-grid.tsx) | UI/data-surface/shell/chart component (virtualized grid). Exports: VirtualizedGrid. |
| [frontend/src/components/drawers/calculation-drawer.tsx](frontend/src/components/drawers/calculation-drawer.tsx) | UI/data-surface/shell/chart component (calculation drawer). Exports: CalculationDrawer. |
| [frontend/src/components/drawers/detail-drawer.tsx](frontend/src/components/drawers/detail-drawer.tsx) | UI/data-surface/shell/chart component (detail drawer). Exports: DetailDrawer. |
| [frontend/src/components/drawers/mobile-bottom-sheet.tsx](frontend/src/components/drawers/mobile-bottom-sheet.tsx) | UI/data-surface/shell/chart component (mobile bottom sheet). Exports: MobileBottomSheet. |
| [frontend/src/components/kpi/kpi-card.tsx](frontend/src/components/kpi/kpi-card.tsx) | UI/data-surface/shell/chart component (kpi card). Exports: KpiCard. |
| [frontend/src/components/kpi/primary-kpi-card.tsx](frontend/src/components/kpi/primary-kpi-card.tsx) | UI/data-surface/shell/chart component (primary kpi card). Exports: PrimaryKpiCard. |
| [frontend/src/components/kpi/secondary-kpi-card.tsx](frontend/src/components/kpi/secondary-kpi-card.tsx) | UI/data-surface/shell/chart component (secondary kpi card). Exports: SecondaryKpiCard. |
| [frontend/src/components/layout/page-action-bar.tsx](frontend/src/components/layout/page-action-bar.tsx) | UI/data-surface/shell/chart component (page action bar). Exports: PageActionBar. |
| [frontend/src/components/layout/page-container.tsx](frontend/src/components/layout/page-container.tsx) | UI/data-surface/shell/chart component (page container). Exports: PageContainer. |
| [frontend/src/components/layout/page-header.tsx](frontend/src/components/layout/page-header.tsx) | UI/data-surface/shell/chart component (page header). Exports: PageHeader. |
| [frontend/src/components/layout/panel.tsx](frontend/src/components/layout/panel.tsx) | UI/data-surface/shell/chart component (panel). Exports: Panel, PanelHeader, PanelBody, PanelFooter. |
| [frontend/src/components/layout/right-rail.tsx](frontend/src/components/layout/right-rail.tsx) | UI/data-surface/shell/chart component (right rail). Exports: RightRail. |
| [frontend/src/components/layout/status-strip.tsx](frontend/src/components/layout/status-strip.tsx) | UI/data-surface/shell/chart component (status strip). Exports: StatusItem, StatusStrip. |
| [frontend/src/components/layout/tab-nav.tsx](frontend/src/components/layout/tab-nav.tsx) | UI/data-surface/shell/chart component (tab nav). Exports: TabNavItem, TabNav. |
| [frontend/src/components/reports/latest-report-card.tsx](frontend/src/components/reports/latest-report-card.tsx) | UI/data-surface/shell/chart component (latest report card). Exports: LatestReportCard. |
| [frontend/src/components/reports/report-history-list.tsx](frontend/src/components/reports/report-history-list.tsx) | UI/data-surface/shell/chart component (report history list). Exports: ReportHistoryList. |
| [frontend/src/components/reports/report-job-status-panel.tsx](frontend/src/components/reports/report-job-status-panel.tsx) | UI/data-surface/shell/chart component (report job status panel). Exports: ReportJobStatusPanel. |
| [frontend/src/components/reports/report-preview-frame.tsx](frontend/src/components/reports/report-preview-frame.tsx) | UI/data-surface/shell/chart component (report preview frame). Exports: ReportPreviewFrame. |
| [frontend/src/components/reports/schedule-report-card.tsx](frontend/src/components/reports/schedule-report-card.tsx) | UI/data-surface/shell/chart component (schedule report card). Exports: ScheduleReportCard. |
| [frontend/src/components/safety/confirm-action-dialog.tsx](frontend/src/components/safety/confirm-action-dialog.tsx) | UI/data-surface/shell/chart component (confirm action dialog). Exports: ConfirmActionDialog. |
| [frontend/src/components/safety/field-help-callout.tsx](frontend/src/components/safety/field-help-callout.tsx) | UI/data-surface/shell/chart component (field help callout). Exports: FieldHelpCallout. |
| [frontend/src/components/safety/form-section.tsx](frontend/src/components/safety/form-section.tsx) | UI/data-surface/shell/chart component (form section). Exports: FormSection. |
| [frontend/src/components/safety/inline-validation-hint.tsx](frontend/src/components/safety/inline-validation-hint.tsx) | UI/data-surface/shell/chart component (inline validation hint). Exports: InlineValidationHint. |
| [frontend/src/components/safety/reauth-action-dialog.tsx](frontend/src/components/safety/reauth-action-dialog.tsx) | UI/data-surface/shell/chart component (reauth action dialog). Exports: ReauthActionDialog. |
| [frontend/src/components/safety/role-aware-disabled-hint.tsx](frontend/src/components/safety/role-aware-disabled-hint.tsx) | UI/data-surface/shell/chart component (role aware disabled hint). Exports: RoleAwareDisabledHint. |
| [frontend/src/components/safety/wizard-stepper.tsx](frontend/src/components/safety/wizard-stepper.tsx) | UI/data-surface/shell/chart component (wizard stepper). Exports: WizardStepper. |
| [frontend/src/components/shell/app-shell.tsx](frontend/src/components/shell/app-shell.tsx) | UI/data-surface/shell/chart component (app shell). Exports: AppShell. |
| [frontend/src/components/shell/breadcrumbs.tsx](frontend/src/components/shell/breadcrumbs.tsx) | UI/data-surface/shell/chart component (breadcrumbs). Exports: Breadcrumbs. |
| [frontend/src/components/shell/command-palette.tsx](frontend/src/components/shell/command-palette.tsx) | UI/data-surface/shell/chart component (command palette). Exports: CommandPalette. |
| [frontend/src/components/shell/date-range-control.tsx](frontend/src/components/shell/date-range-control.tsx) | UI/data-surface/shell/chart component (date range control). Exports: DateRangeControl. |
| [frontend/src/components/shell/notification-center.tsx](frontend/src/components/shell/notification-center.tsx) | UI/data-surface/shell/chart component (notification center). Exports: NotificationCenter. |
| [frontend/src/components/shell/onboarding-progress-rail.tsx](frontend/src/components/shell/onboarding-progress-rail.tsx) | UI/data-surface/shell/chart component (onboarding progress rail). Exports: OnboardingProgressRail. |
| [frontend/src/components/shell/primary-nav.tsx](frontend/src/components/shell/primary-nav.tsx) | UI/data-surface/shell/chart component (primary nav). Exports: PrimaryNav. |
| [frontend/src/components/shell/profile-menu.tsx](frontend/src/components/shell/profile-menu.tsx) | UI/data-surface/shell/chart component (profile menu). Exports: ProfileMenu. |
| [frontend/src/components/shell/quick-create-menu.tsx](frontend/src/components/shell/quick-create-menu.tsx) | UI/data-surface/shell/chart component (quick create menu). Exports: QuickCreateMenu. |
| [frontend/src/components/shell/secondary-nav.tsx](frontend/src/components/shell/secondary-nav.tsx) | UI/data-surface/shell/chart component (secondary nav). Exports: SecondaryNav. |
| [frontend/src/components/shell/top-bar.tsx](frontend/src/components/shell/top-bar.tsx) | UI/data-surface/shell/chart component (top bar). Exports: TopBar. |
| [frontend/src/components/states/inline-error-banner.tsx](frontend/src/components/states/inline-error-banner.tsx) | UI/data-surface/shell/chart component (inline error banner). Exports: InlineErrorBanner. |
| [frontend/src/components/states/mutation-progress-toast.tsx](frontend/src/components/states/mutation-progress-toast.tsx) | UI/data-surface/shell/chart component (mutation progress toast). Exports: MutationProgressToast. |
| [frontend/src/components/states/permission-state.tsx](frontend/src/components/states/permission-state.tsx) | UI/data-surface/shell/chart component (permission state). Exports: PermissionState. |
| [frontend/src/components/states/retry-card.tsx](frontend/src/components/states/retry-card.tsx) | UI/data-surface/shell/chart component (retry card). Exports: RetryCard. |
| [frontend/src/components/states/skeleton-panel.tsx](frontend/src/components/states/skeleton-panel.tsx) | UI/data-surface/shell/chart component (skeleton panel). Exports: SkeletonPanel. |
| [frontend/src/components/states/skeleton-state.tsx](frontend/src/components/states/skeleton-state.tsx) | UI/data-surface/shell/chart component (skeleton state). Exports: SkeletonState. |
| [frontend/src/components/states/success-state-card.tsx](frontend/src/components/states/success-state-card.tsx) | UI/data-surface/shell/chart component (success state card). Exports: SuccessStateCard. |
| [frontend/src/components/states/success-state.tsx](frontend/src/components/states/success-state.tsx) | UI/data-surface/shell/chart component (success state). Exports: SuccessState. |
| [frontend/src/components/ui/badge.tsx](frontend/src/components/ui/badge.tsx) | UI/data-surface/shell/chart component (badge). Exports: BadgeProps. |
| [frontend/src/components/ui/button.tsx](frontend/src/components/ui/button.tsx) | UI/data-surface/shell/chart component (button). Exports: ButtonProps. |
| [frontend/src/components/ui/card.tsx](frontend/src/components/ui/card.tsx) | UI/data-surface/shell/chart component (card). Exports: Card, CardHeader, CardTitle, CardDescription, CardContent. |
| [frontend/src/components/ui/dialog.tsx](frontend/src/components/ui/dialog.tsx) | UI/data-surface/shell/chart component (dialog). Exports: Dialog, DialogTrigger, DialogPortal, DialogClose, DialogOverlay, DialogContent, DialogHeader, DialogTitle, DialogDescription. |
| [frontend/src/components/ui/input.tsx](frontend/src/components/ui/input.tsx) | UI/data-surface/shell/chart component (input). Exports: Input. |
| [frontend/src/components/ui/select.tsx](frontend/src/components/ui/select.tsx) | UI/data-surface/shell/chart component (select). See source declarations. |
| [frontend/src/components/ui/skeleton.tsx](frontend/src/components/ui/skeleton.tsx) | UI/data-surface/shell/chart component (skeleton). Exports: Skeleton. |
| [frontend/src/features/activity/admin-console-page.tsx](frontend/src/features/activity/admin-console-page.tsx) | Feature module for activity (admin console page). Exports: AdminConsolePage. |
| [frontend/src/features/activity/hooks.ts](frontend/src/features/activity/hooks.ts) | Feature module for activity (hooks). Exports: JobFilters, OutboxFilters, useJobs, useAnalyticsRecompute, useAdminRecompute, useOutbox, useSystemStatus, useRuntimeSlos, useRuntimeMetrics, DeadLetterFilters, useDeadLetter, useRetryOutboxEvent, useReplayDeadLetter, useDismissDeadLetter, useRetryJob, useCancelJob, usePauseSchedule, useResumeSchedule, useRunSchedule, AuditExportParams, useRotateOrgPii, useAuditExport, useDeletionRequests. |
| [frontend/src/features/activity/panels/dead-letter-tab-panel.tsx](frontend/src/features/activity/panels/dead-letter-tab-panel.tsx) | Feature module for activity (dead letter tab panel). Exports: DeadLetterTabPanel. |
| [frontend/src/features/activity/panels/jobs-tab-panel.tsx](frontend/src/features/activity/panels/jobs-tab-panel.tsx) | Feature module for activity (jobs tab panel). Exports: JobsTabPanel. |
| [frontend/src/features/activity/panels/outbox-tab-panel.tsx](frontend/src/features/activity/panels/outbox-tab-panel.tsx) | Feature module for activity (outbox tab panel). Exports: OutboxTabPanel. |
| [frontend/src/features/activity/panels/runtime-tab-panel.tsx](frontend/src/features/activity/panels/runtime-tab-panel.tsx) | Feature module for activity (runtime tab panel). Exports: RuntimeTabPanel. |
| [frontend/src/features/activity/panels/security-ops-tab-panel.tsx](frontend/src/features/activity/panels/security-ops-tab-panel.tsx) | Feature module for activity (security ops tab panel). Exports: SecurityOpsTabPanel. |
| [frontend/src/features/ai-chat/containers/assistant-workspace-container.tsx](frontend/src/features/ai-chat/containers/assistant-workspace-container.tsx) | Feature module for ai-chat (assistant workspace container). Exports: AssistantWorkspaceContainer. |
| [frontend/src/features/ai-chat/hooks.ts](frontend/src/features/ai-chat/hooks.ts) | Feature module for ai-chat (hooks). Exports: useAiChatSessions, useAiChatSession, useCreateAiChatSession, useSendAiChatMessage. |
| [frontend/src/features/ai-chat/services/suggested-prompts.ts](frontend/src/features/ai-chat/services/suggested-prompts.ts) | Feature module for ai-chat (suggested prompts). Exports: buildSuggestedPrompts. |
| [frontend/src/features/alerts/containers/alerts-workspace-container.tsx](frontend/src/features/alerts/containers/alerts-workspace-container.tsx) | Feature module for alerts (alerts workspace container). Exports: AlertsWorkspaceContainer. |
| [frontend/src/features/alerts/hooks.ts](frontend/src/features/alerts/hooks.ts) | Feature module for alerts (hooks). Exports: useAlerts, useDismissAlert, useAssignAlert, useAcknowledgeAlert, useAlertHistory. |
| [frontend/src/features/alerts/panels/alert-action-panel.tsx](frontend/src/features/alerts/panels/alert-action-panel.tsx) | Feature module for alerts (alert action panel). Exports: AlertActionPanel. |
| [frontend/src/features/alerts/panels/alert-detail-panel.tsx](frontend/src/features/alerts/panels/alert-detail-panel.tsx) | Feature module for alerts (alert detail panel). Exports: AlertDetailPanel. |
| [frontend/src/features/alerts/panels/alert-feed-panel.tsx](frontend/src/features/alerts/panels/alert-feed-panel.tsx) | Feature module for alerts (alert feed panel). Exports: AlertFeedPanel. |
| [frontend/src/features/alerts/services/recommendations.ts](frontend/src/features/alerts/services/recommendations.ts) | Feature module for alerts (recommendations). Exports: AlertRecommendationAction, AlertRecommendation, getAlertRecommendations. |
| [frontend/src/features/auth/hooks.ts](frontend/src/features/auth/hooks.ts) | Feature module for auth (hooks). Exports: useLogin, useRegister, useConfirmRegistration, useAcceptInvite, useResendConfirmation. |
| [frontend/src/features/auth/login-form.tsx](frontend/src/features/auth/login-form.tsx) | Feature module for auth (login form). Exports: LoginForm. |
| [frontend/src/features/auth/register-form.tsx](frontend/src/features/auth/register-form.tsx) | Feature module for auth (register form). Exports: RegisterForm. |
| [frontend/src/features/budgets/containers/budgets-workspace-container.tsx](frontend/src/features/budgets/containers/budgets-workspace-container.tsx) | Feature module for budgets (budgets workspace container). Exports: BudgetsWorkspaceContainer. |
| [frontend/src/features/budgets/hooks.ts](frontend/src/features/budgets/hooks.ts) | Feature module for budgets (hooks). Exports: normalizeBudgetPeriodForApi, useBudgets, useCreateBudget, useUpdateBudget, useBudgetVariance. |
| [frontend/src/features/budgets/panels/planned-vs-actual-chart-panel.tsx](frontend/src/features/budgets/panels/planned-vs-actual-chart-panel.tsx) | Feature module for budgets (planned vs actual chart panel). Exports: PlannedVsActualChartPanel. |
| [frontend/src/features/budgets/panels/version-compare-panel.tsx](frontend/src/features/budgets/panels/version-compare-panel.tsx) | Feature module for budgets (version compare panel). Exports: VersionComparePanel. |
| [frontend/src/features/dashboard/dashboard-page-client.tsx](frontend/src/features/dashboard/dashboard-page-client.tsx) | Feature module for dashboard (dashboard page client). Exports: DashboardPageClient. |
| [frontend/src/features/dashboard/hooks.ts](frontend/src/features/dashboard/hooks.ts) | Feature module for dashboard (hooks). Exports: useDashboardData. |
| [frontend/src/features/dashboard/panels/alert-detail-drawer.tsx](frontend/src/features/dashboard/panels/alert-detail-drawer.tsx) | Feature module for dashboard (alert detail drawer). Exports: AlertDetailDrawer. |
| [frontend/src/features/dashboard/panels/benchmark-panel.tsx](frontend/src/features/dashboard/panels/benchmark-panel.tsx) | Feature module for dashboard (benchmark panel). Exports: BenchmarkPanel. |
| [frontend/src/features/dashboard/panels/cashflow-chart-panel.tsx](frontend/src/features/dashboard/panels/cashflow-chart-panel.tsx) | Feature module for dashboard (cashflow chart panel). Exports: CashflowChartPanel. |
| [frontend/src/features/dashboard/panels/hero-strip.tsx](frontend/src/features/dashboard/panels/hero-strip.tsx) | Feature module for dashboard (hero strip). Exports: HeroStrip. |
| [frontend/src/features/dashboard/panels/kpi-grid.tsx](frontend/src/features/dashboard/panels/kpi-grid.tsx) | Feature module for dashboard (kpi grid). Exports: DashboardKpiGrid. |
| [frontend/src/features/dashboard/panels/priority-alerts-panel.tsx](frontend/src/features/dashboard/panels/priority-alerts-panel.tsx) | Feature module for dashboard (priority alerts panel). Exports: PriorityAlertsPanel. |
| [frontend/src/features/dashboard/panels/revenue-expense-chart-panel.tsx](frontend/src/features/dashboard/panels/revenue-expense-chart-panel.tsx) | Feature module for dashboard (revenue expense chart panel). Exports: RevenueExpenseChartPanel. |
| [frontend/src/features/dashboard/panels/workforce-intelligence-panel.tsx](frontend/src/features/dashboard/panels/workforce-intelligence-panel.tsx) | Feature module for dashboard (workforce intelligence panel). Exports: WorkforceIntelligencePanel. |
| [frontend/src/features/forecast/containers/forecast-workspace-container.tsx](frontend/src/features/forecast/containers/forecast-workspace-container.tsx) | Feature module for forecast (forecast workspace container). Exports: ForecastWorkspaceContainer. |
| [frontend/src/features/forecast/hooks.ts](frontend/src/features/forecast/hooks.ts) | Feature module for forecast (hooks). Exports: useForecast, useForecastOverride. |
| [frontend/src/features/forecast/panels/assumptions-panel.tsx](frontend/src/features/forecast/panels/assumptions-panel.tsx) | Feature module for forecast (assumptions panel). Exports: ForecastAssumptions, AssumptionsPanel. |
| [frontend/src/features/forecast/panels/risk-panel.tsx](frontend/src/features/forecast/panels/risk-panel.tsx) | Feature module for forecast (risk panel). Exports: RiskPanel. |
| [frontend/src/features/forecast/panels/sensitivity-panel.tsx](frontend/src/features/forecast/panels/sensitivity-panel.tsx) | Feature module for forecast (sensitivity panel). Exports: SensitivityPanel. |
| [frontend/src/features/inventory/containers/inventory-workspace-container.tsx](frontend/src/features/inventory/containers/inventory-workspace-container.tsx) | Feature module for inventory (inventory workspace container). Exports: InventoryWorkspaceContainer. |
| [frontend/src/features/inventory/hooks.ts](frontend/src/features/inventory/hooks.ts) | Feature module for inventory (hooks). Exports: useInventoryItems, useInventoryForecast, useCreateInventoryItem, useCreateInventoryStockEvent, useCreateInventoryPurchaseOrder. |
| [frontend/src/features/inventory/panels/inventory-detail-drawer.tsx](frontend/src/features/inventory/panels/inventory-detail-drawer.tsx) | Feature module for inventory (inventory detail drawer). Exports: InventoryDetailDrawer. |
| [frontend/src/features/locations/hooks.ts](frontend/src/features/locations/hooks.ts) | Feature module for locations (hooks). Exports: useLocations, useCreateLocation, useUpdateLocation, useDeactivateLocation. |
| [frontend/src/features/notifications/hooks.ts](frontend/src/features/notifications/hooks.ts) | Feature module for notifications (hooks). Exports: useOrgEventFeed. |
| [frontend/src/features/notifications/inbox-hooks.ts](frontend/src/features/notifications/inbox-hooks.ts) | Feature module for notifications (inbox hooks). Exports: useNotifications, useMarkNotificationRead, useMarkAllNotificationsRead. |
| [frontend/src/features/onboarding/containers/onboarding-workspace-container.tsx](frontend/src/features/onboarding/containers/onboarding-workspace-container.tsx) | Feature module for onboarding (onboarding workspace container). Exports: OnboardingWorkspaceContainer. |
| [frontend/src/features/onboarding/hooks.ts](frontend/src/features/onboarding/hooks.ts) | Feature module for onboarding (hooks). Exports: OnboardingStep, useOnboardingProgress. |
| [frontend/src/features/orgs/containers/orgs-workspace-container.tsx](frontend/src/features/orgs/containers/orgs-workspace-container.tsx) | Feature module for orgs (orgs workspace container). Exports: OrgsWorkspaceContainer. |
| [frontend/src/features/orgs/hooks.ts](frontend/src/features/orgs/hooks.ts) | Feature module for orgs (hooks). Exports: useOrgs, useCreateOrg, useSelectedOrgRole. |
| [frontend/src/features/reports/containers/reports-workspace-container.tsx](frontend/src/features/reports/containers/reports-workspace-container.tsx) | Feature module for reports (reports workspace container). Exports: ReportsWorkspaceContainer. |
| [frontend/src/features/reports/hooks.ts](frontend/src/features/reports/hooks.ts) | Feature module for reports (hooks). Exports: useWorkforceReportsSummary, useReports, useGenerateReport, fetchReportDownload. |
| [frontend/src/features/reports/reports-page-client.tsx](frontend/src/features/reports/reports-page-client.tsx) | Feature module for reports (reports page client). Exports: ReportsPageClient. |
| [frontend/src/features/settings/hooks.ts](frontend/src/features/settings/hooks.ts) | Feature module for settings (hooks). Exports: useOrgMembers, useInviteMember, useOrgSettings, useUpdateOrgSettings, usePlanUsage, useBankConnections, usePlaidLinkToken, usePlaidExchange, useSyncBankConnection, useDeleteBankConnection, usePaymentConnections, useStripeConnect, usePaymentReconciliation, useOrgBilling, useUpdateOrgBilling, useBillingCheckout, useBillingPortal, useAuthReauth, useMfaStatus, useMfaSetup, useMfaEnable, useMfaDisable, useMfaRegenerateRecoveryCodes, useAuthSessions, useRevokeSession, useRevokeOtherSessions, useRequestAccountDeletion, useRequestOrgDeletion, useMyDeletionRequests, useOrgDeletionRequests. |
| [frontend/src/features/settings/panels/billing-panel.tsx](frontend/src/features/settings/panels/billing-panel.tsx) | Feature module for settings (billing panel). Exports: BillingPanel. |
| [frontend/src/features/settings/panels/compliance-panel.tsx](frontend/src/features/settings/panels/compliance-panel.tsx) | Feature module for settings (compliance panel). Exports: CompliancePanel. |
| [frontend/src/features/settings/panels/danger-panel.tsx](frontend/src/features/settings/panels/danger-panel.tsx) | Feature module for settings (danger panel). Exports: DangerPanel. |
| [frontend/src/features/settings/panels/general-panel.tsx](frontend/src/features/settings/panels/general-panel.tsx) | Feature module for settings (general panel). Exports: GeneralPanel. |
| [frontend/src/features/settings/panels/integrations-panel.tsx](frontend/src/features/settings/panels/integrations-panel.tsx) | Feature module for settings (integrations panel). Exports: IntegrationsPanel. |
| [frontend/src/features/settings/panels/security-panel.tsx](frontend/src/features/settings/panels/security-panel.tsx) | Feature module for settings (security panel). Exports: SecurityPanel. |
| [frontend/src/features/settings/panels/team-panel.tsx](frontend/src/features/settings/panels/team-panel.tsx) | Feature module for settings (team panel). Exports: TeamPanel. |
| [frontend/src/features/settings/services/use-settings-service-adapter.ts](frontend/src/features/settings/services/use-settings-service-adapter.ts) | Feature module for settings (use settings service adapter). Exports: useSettingsServiceAdapter. |
| [frontend/src/features/transactions/containers/transactions-workspace-container.tsx](frontend/src/features/transactions/containers/transactions-workspace-container.tsx) | Feature module for transactions (transactions workspace container). Exports: TransactionsWorkspaceContainer. |
| [frontend/src/features/transactions/hooks.ts](frontend/src/features/transactions/hooks.ts) | Feature module for transactions (hooks). Exports: TransactionFilters, AlertRecalcMetadata, useTransactions, useCreateTransaction, useUpdateTransaction, useDeleteTransaction, importCsv, useImportProfiles, useCreateImportProfile, useUpdateImportProfile, useDeleteImportProfile, useBulkRemapCategory, useImportHistory, downloadImportErrors. |
| [frontend/src/features/transactions/panels/bulk-remap-workspace-panel.tsx](frontend/src/features/transactions/panels/bulk-remap-workspace-panel.tsx) | Feature module for transactions (bulk remap workspace panel). Exports: BulkRemapWorkspacePanel. |
| [frontend/src/features/transactions/panels/bulk-selection-bar.tsx](frontend/src/features/transactions/panels/bulk-selection-bar.tsx) | Feature module for transactions (bulk selection bar). Exports: BulkSelectionBar. |
| [frontend/src/features/transactions/panels/category-breakdown-panel.tsx](frontend/src/features/transactions/panels/category-breakdown-panel.tsx) | Feature module for transactions (category breakdown panel). Exports: CategoryBreakdownPanel. |
| [frontend/src/features/transactions/panels/create-transaction-dialog.tsx](frontend/src/features/transactions/panels/create-transaction-dialog.tsx) | Feature module for transactions (create transaction dialog). Exports: CreateTransactionDialog. |
| [frontend/src/features/transactions/panels/edit-transaction-dialog.tsx](frontend/src/features/transactions/panels/edit-transaction-dialog.tsx) | Feature module for transactions (edit transaction dialog). Exports: EditTransactionDialog. |
| [frontend/src/features/transactions/panels/import-history-panel.tsx](frontend/src/features/transactions/panels/import-history-panel.tsx) | Feature module for transactions (import history panel). Exports: ImportHistoryPanel. |
| [frontend/src/features/transactions/panels/selected-transaction-panel.tsx](frontend/src/features/transactions/panels/selected-transaction-panel.tsx) | Feature module for transactions (selected transaction panel). Exports: SelectedTransactionPanel. |
| [frontend/src/features/transactions/panels/transactions-import-dialog.tsx](frontend/src/features/transactions/panels/transactions-import-dialog.tsx) | Feature module for transactions (transactions import dialog). Exports: TransactionsImportDialog. |
| [frontend/src/features/transactions/services/csv.ts](frontend/src/features/transactions/services/csv.ts) | Feature module for transactions (csv). Exports: CsvField, CsvMapping, CsvRawRow, csvFields, csvMaxBytes, parseCsvContent, autoDetectMapping, mappingToApiPayload. |
| [frontend/src/features/transactions/services/saved-views.ts](frontend/src/features/transactions/services/saved-views.ts) | Feature module for transactions (saved views). Exports: SavedTransactionView, loadSavedTransactionViews, persistSavedTransactionViews, persistActiveTransactionView. |
| [frontend/src/features/workforce/containers/employee-detail-client.tsx](frontend/src/features/workforce/containers/employee-detail-client.tsx) | Feature module for workforce (employee detail client). Exports: EmployeeDetailClient. |
| [frontend/src/features/workforce/hooks.ts](frontend/src/features/workforce/hooks.ts) | Feature module for workforce (hooks). Exports: useWorkforceDepartments, useCreateWorkforceDepartment, useUpdateWorkforceDepartment, useDeactivateWorkforceDepartment, useWorkforceTitles, useCreateWorkforceTitle, useUpdateWorkforceTitle, useDeactivateWorkforceTitle, useWorkforceEmployees, useWorkforceEmployee, useCreateWorkforceEmployee, useUpdateWorkforceEmployee, useDeactivateWorkforceEmployee, useWorkforceShifts, useCreateWorkforceShift, useUpdateWorkforceShift, useDeactivateWorkforceShift, useWorkforceShiftAssignments, useCreateWorkforceShiftAssignment, useWorkforceAttendanceDaily, useWorkforceAttendanceCalendar, useClockIn, useClockOut, useManualAttendanceEntry, useWorkforceCorrections, useRequestCorrection, useReviewCorrection, useWorkforceLeaveTypes, useCreateWorkforceLeaveType, useUpdateWorkforceLeaveType, useDeactivateWorkforceLeaveType, useWorkforceLeaveBalances, useAllocateWorkforceLeaveBalance, useWorkforceLeaveRequests, useCreateWorkforceLeaveRequest, useDecideWorkforceLeaveRequest, useWorkforceAnnouncements, useWorkforceAnnouncementDetail, useWorkforceAnnouncementTemplates, useCreateWorkforceAnnouncementTemplate, useUpdateWorkforceAnnouncementTemplate, useWorkforceAnnouncementAutomationKeys, uploadWorkforceAnnouncementAttachment, useWorkforceAnnouncementDeliveries, useCreateWorkforceAnnouncement, useUpdateWorkforceAnnouncement, usePublishWorkforceAnnouncement, useArchiveWorkforceAnnouncement, useAcknowledgeWorkforceAnnouncement, useWorkforcePayrollPeriods, useCreateWorkforcePayrollPeriod, useGenerateWorkforcePayrollDraft, useWorkforcePayrollEntries, useApproveWorkforcePayrollPeriod, useMarkPaidWorkforcePayrollPeriod, useCreateWorkforcePayrollAdjustment, useDeleteWorkforcePayrollAdjustment, useWorkforcePayslipPreview, useWorkforcePolicies, useCreateWorkforcePolicy, usePublishWorkforcePolicy, useWorkforcePolicyAcks, useAcknowledgeWorkforcePolicy, useWorkforceDocuments, uploadWorkforceHrDocument, useDeactivateWorkforceHrDocument, useWorkforceChecklist, useCreateWorkforceChecklistItem, useSetWorkforceChecklistDone. |
| [frontend/src/features/workforce/panels/employee-dialog.tsx](frontend/src/features/workforce/panels/employee-dialog.tsx) | Feature module for workforce (employee dialog). Exports: EmployeeDialog. |
| [frontend/src/features/workforce/panels/workforce-settings-panel.tsx](frontend/src/features/workforce/panels/workforce-settings-panel.tsx) | Feature module for workforce (workforce settings panel). Exports: WorkforceSettingsPanel. |
| [frontend/src/lib/api/client.ts](frontend/src/lib/api/client.ts) | Client API/auth/query/utility/UX module (client). Exports: ApiError, apiFetchRaw, api, bootstrapSession, logout. |
| [frontend/src/lib/api/endpoints.ts](frontend/src/lib/api/endpoints.ts) | Client API/auth/query/utility/UX module (endpoints). Exports: apiPaths. |
| [frontend/src/lib/api/events.ts](frontend/src/lib/api/events.ts) | Client API/auth/query/utility/UX module (events). Exports: ApiClientEventDetail, API_CLIENT_EVENT_NAME, emitApiClientEvent. |
| [frontend/src/lib/api/schemas.ts](frontend/src/lib/api/schemas.ts) | Client API/auth/query/utility/UX module (schemas). Exports: tokenSchema, meSchema, summarySchema, aiSummarySchema, aiChatSessionSchema, aiChatMessageSchema, aiChatSessionDetailSchema, aiChatResponseSchema, registerOutSchema, resendConfirmationSchema, reportGenerateSchema, jobSchema, jobPageSchema, outboxEventSchema, outboxPageSchema, beatScheduleSchema, systemStatusSchema, endpointSloSchema, runtimeSloSchema, runtimeMetricsSchema, deadLetterEventSchema, deadLetterPageSchema, notificationItemSchema, notificationPageSchema, billingUrlSchema, deletionRequestItemSchema, deletionRequestListSchema, paymentReconciliationSchema, budgetSchema, budgetVarianceLineSchema, budgetVarianceSchema, locationBenchmarkItemSchema, locationBenchmarkSchema, inventoryItemSchema, inventoryStockEventSchema, inventoryPurchaseOrderSchema, inventoryForecastItemSchema, inventoryForecastSchema, workforceDepartmentSchema, workforceTitleSchema, workforceEmployeeSchema, workforcePolicySchema, workforcePolicyAckSchema, workforceDocumentSchema, workforceChecklistItemSchema, workforceShiftSchema, workforceShiftAssignmentSchema, workforceAttendanceSchema, workforceAttendanceDailySchema, workforceAttendanceCalendarDaySchema, workforceAttendanceCalendarSchema, workforceAttendanceCorrectionSchema, workforceLeaveTypeSchema, workforceLeaveBalanceSchema, workforceAnnouncementReceiptSchema, workforceAnnouncementAttachmentSchema, workforceAnnouncementSchema, workforceAnnouncementTemplateSchema, workforceAnnouncementDeliverySchema, workforceAnnouncementDeliveryListSchema, workforceAnnouncementAttachmentUploadSchema, workforceAutomationKeysSchema, workforceLeaveRequestSchema, workforcePayrollPeriodSchema, workforcePayrollEntrySchema, workforcePayrollAdjustmentSchema, workforcePayslipPreviewSchema, workforceDepartmentHeadcountRowSchema, workforceLaborCostPeriodRowSchema, workforceDashboardIntelSchema, workforceReportsSummarySchema, TokenResponse, MeResponse, SummaryResponse, AiSummaryResponse, AiChatSessionResponse, AiChatMessageResponse, AiChatSessionDetailResponse, AiChatResponse, RegisterOutResponse, ResendConfirmationResponse, ReportGenerateResponse, JobPageResponse, OutboxPageResponse, SystemStatusResponse, RuntimeSloResponse, RuntimeMetricsResponse, DeadLetterPageResponse, NotificationPageResponse, BillingUrlResponse, DeletionRequestListResponse, PaymentReconciliationResponse, BudgetResponse, BudgetVarianceResponse, LocationBenchmarkResponse, InventoryItemResponse, InventoryStockEventResponse, InventoryPurchaseOrderResponse, InventoryForecastResponse, WorkforceDepartmentResponse, WorkforceTitleResponse, WorkforceEmployeeResponse, WorkforceShiftResponse, WorkforceShiftAssignmentResponse, WorkforceAttendanceResponse, WorkforceAttendanceDailyResponse, WorkforceAttendanceCalendarResponse, WorkforceAttendanceCorrectionResponse, WorkforceLeaveTypeResponse, WorkforceLeaveBalanceResponse, WorkforceAnnouncementResponse, WorkforceLeaveRequestResponse, WorkforcePayrollPeriodResponse, WorkforcePayrollEntryResponse, WorkforcePayrollAdjustmentResponse, WorkforcePayslipPreviewResponse, WorkforceDashboardIntelResponse, WorkforceReportsSummaryResponse. |
| [frontend/src/lib/api/server.ts](frontend/src/lib/api/server.ts) | Client API/auth/query/utility/UX module (server). Exports: getServerSelectedOrgId, serverApiGet, serverApiPost, resolveServerOrgId. |
| [frontend/src/lib/api/types.ts](frontend/src/lib/api/types.ts) | Client API/auth/query/utility/UX module (types). See source declarations. |
| [frontend/src/lib/auth/rbac.ts](frontend/src/lib/auth/rbac.ts) | Client API/auth/query/utility/UX module (rbac). Exports: canEdit, isOwner. |
| [frontend/src/lib/auth/session.ts](frontend/src/lib/auth/session.ts) | Client API/auth/query/utility/UX module (session). Exports: useSessionBootstrap. |
| [frontend/src/lib/auth/tokens.ts](frontend/src/lib/auth/tokens.ts) | Client API/auth/query/utility/UX module (tokens). Exports: getAccessToken, getRefreshToken, setTokens, clearTokens. |
| [frontend/src/lib/auth/useRouteGuard.ts](frontend/src/lib/auth/useRouteGuard.ts) | Client API/auth/query/utility/UX module (useRouteGuard). Exports: useRouteGuard. |
| [frontend/src/lib/query/keys.ts](frontend/src/lib/query/keys.ts) | Client API/auth/query/utility/UX module (keys). Exports: qk. |
| [frontend/src/lib/query/prefetch.ts](frontend/src/lib/query/prefetch.ts) | Client API/auth/query/utility/UX module (prefetch). Exports: createServerQueryClient, prefetchDashboard, prefetchReports. |
| [frontend/src/lib/query/queryClient.ts](frontend/src/lib/query/queryClient.ts) | Client API/auth/query/utility/UX module (queryClient). Exports: createQueryClient. |
| [frontend/src/lib/utils/chart.ts](frontend/src/lib/utils/chart.ts) | Client API/auth/query/utility/UX module (chart). Exports: NumericSeriesPoint, downsamplePoints, toNumber, CategoryBreakdownRow, buildCategoryBreakdown, alertImpactValue, normalizeImpact, computeChartDomain. |
| [frontend/src/lib/utils/cn.ts](frontend/src/lib/utils/cn.ts) | Client API/auth/query/utility/UX module (cn). Exports: cn. |
| [frontend/src/lib/utils/format.ts](frontend/src/lib/utils/format.ts) | Client API/auth/query/utility/UX module (format). Exports: formatMoney, formatCompactMoney, formatDate, formatMonth, formatPercent, formatDelta, startOfMonthISO, todayISO, weekStartISO, shiftDaysISO, daysBetween. |
| [frontend/src/lib/utils/use-is-md-up.ts](frontend/src/lib/utils/use-is-md-up.ts) | Client API/auth/query/utility/UX module (use is md up). Exports: MD_BREAKPOINT_PX, useIsMdUp. |
| [frontend/src/lib/ux/experience.ts](frontend/src/lib/ux/experience.ts) | Client API/auth/query/utility/UX module (experience). Exports: isTierAtLeast, canAccessAdvancedNav, defaultTierForRole, isSimpleTier. |
| [frontend/src/store/appStore.ts](frontend/src/store/appStore.ts) | Zustand application context/selection state. Exports: OrgRole, ExperienceTier, MeOrg, MeUser, useAppStore. |
| [frontend/src/types/domain.ts](frontend/src/types/domain.ts) | Domain/external integration TypeScript declarations. Exports: Role, Org, Member, Transaction, PaginatedTransactions, Summary, AiChatSession, AiChatMessage, AiChatSessionDetail, Budget, BudgetVarianceLine, BudgetVariance, Cashflow, Runway, ForecastPoint, Forecast, Alert, AlertHistoryItem, Report, InventoryItem, InventoryStockEvent, InventoryPurchaseOrder, InventoryForecastItem, InventoryForecast, Location, WorkforceDepartment, WorkforceTitle, WorkforceEmployee, WorkforcePolicy, WorkforcePolicyAck, WorkforceDocument, WorkforceChecklistItem, WorkforceShift, WorkforceShiftAssignment, WorkforceAttendance, WorkforceAttendanceDaily, WorkforceAttendanceCalendarDay, WorkforceAttendanceCalendar, WorkforceAttendanceCorrection, WorkforceAnnouncementReceipt, WorkforceAnnouncementAttachment, WorkforceAnnouncement, WorkforceAnnouncementTemplate, WorkforceAnnouncementDelivery, WorkforceAnnouncementDeliveryList, WorkforceLeaveType, WorkforceLeaveBalance, WorkforceLeaveRequest, WorkforcePayrollPeriod, WorkforcePayrollEntry, WorkforcePayrollAdjustment, WorkforcePayslipPreview, OrgSettings, OrgBilling, PlanUsage, Job, JobPage, AnalyticsRecomputeResult, AdminRecomputeResult, ResendConfirmationResult, ReportGenerationResult, OutboxEvent, OutboxPage, BeatScheduleItem, SystemStatus, EndpointSLO, RuntimeSLO, StreamUpdate, ImportHistoryItem, ImportHistoryPage, ImportMappingProfile, NotificationItem, NotificationPage, MfaStatus, AuthSession, BillingCheckoutResult, BillingPortalResult, DeletionRequestResult, PiiRotationResult, DeletionRequestItem, DeletionRequestList, BankAccount, BankConnection, PlaidLinkTokenResult, PaymentConnection, StripeConnectResult, PaymentReconciliation. |
| [frontend/src/types/plaid-link.d.ts](frontend/src/types/plaid-link.d.ts) | Domain/external integration TypeScript declarations. Exports: PlaidLinkSuccessMetadata, PlaidLinkExitError, PlaidLinkHandler, PlaidCreateConfig, PlaidFactory. |
| [frontend/tailwind.config.ts](frontend/tailwind.config.ts) | Frontend/shared configuration or type module. See source declarations. |
| [frontend/tsconfig.json](frontend/tsconfig.json) | Configuration/generated contract/support artifact: tsconfig.json. |

#### perf-artifacts files

| File | Responsibility |
| --- | --- |
| [perf-artifacts/stage2-closure/bootstrap.json](perf-artifacts/stage2-closure/bootstrap.json) | Historical performance/test/debug/bootstrap artifact: bootstrap. Not fresh verification; payload may contain disposable identities/tokens. |
| [perf-artifacts/stage2-closure/inventory_churn_summary.json](perf-artifacts/stage2-closure/inventory_churn_summary.json) | Historical performance/test/debug/bootstrap artifact: inventory churn summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [perf-artifacts/stage2-closure/mixed_churn_summary.json](perf-artifacts/stage2-closure/mixed_churn_summary.json) | Historical performance/test/debug/bootstrap artifact: mixed churn summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [perf-artifacts/stage2-closure/perf_gate_summary.json](perf-artifacts/stage2-closure/perf_gate_summary.json) | Historical performance/test/debug/bootstrap artifact: perf gate summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [perf-artifacts/stage2-closure/perf_gate_summary.md](perf-artifacts/stage2-closure/perf_gate_summary.md) | Historical performance/test/debug/bootstrap artifact: perf gate summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [perf-artifacts/stage2-closure/read_hotpaths_pass1_summary.json](perf-artifacts/stage2-closure/read_hotpaths_pass1_summary.json) | Historical performance/test/debug/bootstrap artifact: read hotpaths pass1 summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [perf-artifacts/stage2-closure/read_hotpaths_pass2_summary.json](perf-artifacts/stage2-closure/read_hotpaths_pass2_summary.json) | Historical performance/test/debug/bootstrap artifact: read hotpaths pass2 summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [perf-artifacts/stage2-closure/runtime_observability_summary.json](perf-artifacts/stage2-closure/runtime_observability_summary.json) | Historical performance/test/debug/bootstrap artifact: runtime observability summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [perf-artifacts/stage2-closure/seed.log](perf-artifacts/stage2-closure/seed.log) | Historical performance/test/debug/bootstrap artifact: seed. Not fresh verification; payload may contain disposable identities/tokens. |

#### scripts files

| File | Responsibility |
| --- | --- |
| [scripts/loadtest/_shared.js](scripts/loadtest/_shared.js) | Frontend/shared configuration or type module. Exports: requiredEnv, readOrgIds, selectOrg, isoMondayOrToday, commonHeaders. |
| [scripts/loadtest/bootstrap_multi_org_perf.py](scripts/loadtest/bootstrap_multi_org_perf.py) | Python backend/operational/runtime/load tool: bootstrap multi org perf. |
| [scripts/loadtest/bootstrap_perf.py](scripts/loadtest/bootstrap_perf.py) | Python backend/operational/runtime/load tool: bootstrap perf. |
| [scripts/loadtest/evaluate_perf_gates.py](scripts/loadtest/evaluate_perf_gates.py) | Python backend/operational/runtime/load tool: evaluate perf gates. |
| [scripts/loadtest/k6-inventory-churn.js](scripts/loadtest/k6-inventory-churn.js) | Frontend/shared configuration or type module. Exports: options. |
| [scripts/loadtest/k6-many-org-dashboard.js](scripts/loadtest/k6-many-org-dashboard.js) | Frontend/shared configuration or type module. Exports: options. |
| [scripts/loadtest/k6-mixed-churn.js](scripts/loadtest/k6-mixed-churn.js) | Frontend/shared configuration or type module. Exports: options. |
| [scripts/loadtest/k6-read-hotpaths.js](scripts/loadtest/k6-read-hotpaths.js) | Frontend/shared configuration or type module. Exports: options. |
| [scripts/loadtest/k6-report-burst.js](scripts/loadtest/k6-report-burst.js) | Frontend/shared configuration or type module. Exports: options. |
| [scripts/loadtest/k6-runtime-observability.js](scripts/loadtest/k6-runtime-observability.js) | Frontend/shared configuration or type module. Exports: options. |
| [scripts/loadtest/k6-smoke.js](scripts/loadtest/k6-smoke.js) | Frontend/shared configuration or type module. Exports: options. |
| [scripts/loadtest/k6-write-heavy.js](scripts/loadtest/k6-write-heavy.js) | Frontend/shared configuration or type module. Exports: options. |
| [scripts/loadtest/slo_guardrails.json](scripts/loadtest/slo_guardrails.json) | Configuration/generated contract/support artifact: slo_guardrails.json. |
| [scripts/ops/backup_minio.sh](scripts/ops/backup_minio.sh) | Bash backup/restore operation: backup minio. |
| [scripts/ops/backup_postgres.sh](scripts/ops/backup_postgres.sh) | Bash backup/restore operation: backup postgres. |
| [scripts/ops/restore_drill.sh](scripts/ops/restore_drill.sh) | Bash backup/restore operation: restore drill. |
| [scripts/ops/restore_minio.sh](scripts/ops/restore_minio.sh) | Bash backup/restore operation: restore minio. |
| [scripts/ops/restore_postgres.sh](scripts/ops/restore_postgres.sh) | Bash backup/restore operation: restore postgres. |
| [scripts/ops/secret_hygiene_audit.py](scripts/ops/secret_hygiene_audit.py) | Python backend/operational/runtime/load tool: secret hygiene audit. |
| [scripts/ops/verify_ai_live_mode.py](scripts/ops/verify_ai_live_mode.py) | Python backend/operational/runtime/load tool: verify ai live mode. |
| [scripts/seed_load_dataset.py](scripts/seed_load_dataset.py) | Python backend/operational/runtime/load tool: seed load dataset. |
| [scripts/smoke_mvp.py](scripts/smoke_mvp.py) | Python backend/operational/runtime/load tool: smoke mvp. |
| [scripts/smoke_workforce_intelligence.py](scripts/smoke_workforce_intelligence.py) | Python backend/operational/runtime/load tool: smoke workforce intelligence. |
| [scripts/verify_runtime.py](scripts/verify_runtime.py) | Python backend/operational/runtime/load tool: verify runtime. |

#### shared files

| File | Responsibility |
| --- | --- |
| [shared/README.md](shared/README.md) | Shared. Historical/current guidance or proposals; compare with source. |
| [shared/contracts/openapi/openapi.json](shared/contracts/openapi/openapi.json) | Shared generated OpenAPI artifact; can lag live router changes. |
| [shared/demo/transactions_6months.csv](shared/demo/transactions_6months.csv) | Transaction/demo/import fixture. Columns: date,amount,type,category,vendor,notes. |
| [shared/enums/roles.ts](shared/enums/roles.ts) | Frontend/shared configuration or type module. Exports: Role. |

#### test-results files

| File | Responsibility |
| --- | --- |
| [test-results/.last-run.json](test-results/.last-run.json) | Historical performance/test/debug/bootstrap artifact: .last run. Not fresh verification; payload may contain disposable identities/tokens. |

#### testdata files

| File | Responsibility |
| --- | --- |
| [testdata/sample_transactions.csv](testdata/sample_transactions.csv) | Transaction/demo/import fixture. Columns: date,amount,type,category,vendor,notes. |
| [testdata/transactions_full_scenario.csv](testdata/transactions_full_scenario.csv) | Transaction/demo/import fixture. Columns: date,amount,type,category,vendor,notes. |
| [testdata/transactions_invalid_rows.csv](testdata/transactions_invalid_rows.csv) | Transaction/demo/import fixture. Columns: date,amount,type,category,vendor,notes. |
| [testdata/transactions_with_duplicates.csv](testdata/transactions_with_duplicates.csv) | Transaction/demo/import fixture. Columns: date,amount,type,category,vendor,notes. |

#### tmp files

| File | Responsibility |
| --- | --- |
| [tmp/perf/alerts_count.txt](tmp/perf/alerts_count.txt) | Historical performance/test/debug/bootstrap artifact: alerts count. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/alerts_schema.txt](tmp/perf/alerts_schema.txt) | Historical performance/test/debug/bootstrap artifact: alerts schema. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/backend-compare-window-afterfix-ts.log](tmp/perf/backend-compare-window-afterfix-ts.log) | Historical performance/test/debug/bootstrap artifact: backend compare window afterfix ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/backend-compare-window-ts.log](tmp/perf/backend-compare-window-ts.log) | Historical performance/test/debug/bootstrap artifact: backend compare window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/backend-rerun-dbpool-window-ts.log](tmp/perf/backend-rerun-dbpool-window-ts.log) | Historical performance/test/debug/bootstrap artifact: backend rerun dbpool window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/backend-rerun-tuned-window-ts.log](tmp/perf/backend-rerun-tuned-window-ts.log) | Historical performance/test/debug/bootstrap artifact: backend rerun tuned window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/backend-rerun-tuned2-window-ts.log](tmp/perf/backend-rerun-tuned2-window-ts.log) | Historical performance/test/debug/bootstrap artifact: backend rerun tuned2 window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/backend-rerun-tuned3-window-ts.log](tmp/perf/backend-rerun-tuned3-window-ts.log) | Historical performance/test/debug/bootstrap artifact: backend rerun tuned3 window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/backend-rerun-window-ts.log](tmp/perf/backend-rerun-window-ts.log) | Historical performance/test/debug/bootstrap artifact: backend rerun window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/backend-tuned-window-ts.log](tmp/perf/backend-tuned-window-ts.log) | Historical performance/test/debug/bootstrap artifact: backend tuned window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/backend-window-ts.log](tmp/perf/backend-window-ts.log) | Historical performance/test/debug/bootstrap artifact: backend window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/backend-window.log](tmp/perf/backend-window.log) | Historical performance/test/debug/bootstrap artifact: backend window. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/bootstrap_index_pass.json](tmp/perf/bootstrap_index_pass.json) | Historical performance/test/debug/bootstrap artifact: bootstrap index pass. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/bootstrap_perf_after_confirm_fix.json](tmp/perf/bootstrap_perf_after_confirm_fix.json) | Historical performance/test/debug/bootstrap artifact: bootstrap perf after confirm fix. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061640081/perf_gate_summary.fixed.json](tmp/perf/ci-artifacts/run-23061640081/perf_gate_summary.fixed.json) | Historical performance/test/debug/bootstrap artifact: perf gate summary.fixed. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061640081/perf_gate_summary.fixed.md](tmp/perf/ci-artifacts/run-23061640081/perf_gate_summary.fixed.md) | Historical performance/test/debug/bootstrap artifact: perf gate summary.fixed. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061640081/perf_gate_summary.json](tmp/perf/ci-artifacts/run-23061640081/perf_gate_summary.json) | Historical performance/test/debug/bootstrap artifact: perf gate summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061640081/perf_gate_summary.md](tmp/perf/ci-artifacts/run-23061640081/perf_gate_summary.md) | Historical performance/test/debug/bootstrap artifact: perf gate summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061640081/read_hotpaths_pass1_summary.json](tmp/perf/ci-artifacts/run-23061640081/read_hotpaths_pass1_summary.json) | Historical performance/test/debug/bootstrap artifact: read hotpaths pass1 summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061640081/read_hotpaths_pass2_summary.json](tmp/perf/ci-artifacts/run-23061640081/read_hotpaths_pass2_summary.json) | Historical performance/test/debug/bootstrap artifact: read hotpaths pass2 summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061640081/runtime_observability_summary.json](tmp/perf/ci-artifacts/run-23061640081/runtime_observability_summary.json) | Historical performance/test/debug/bootstrap artifact: runtime observability summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061958337/perf_gate_summary.json](tmp/perf/ci-artifacts/run-23061958337/perf_gate_summary.json) | Historical performance/test/debug/bootstrap artifact: perf gate summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061958337/perf_gate_summary.md](tmp/perf/ci-artifacts/run-23061958337/perf_gate_summary.md) | Historical performance/test/debug/bootstrap artifact: perf gate summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061958337/read_hotpaths_pass1_summary.json](tmp/perf/ci-artifacts/run-23061958337/read_hotpaths_pass1_summary.json) | Historical performance/test/debug/bootstrap artifact: read hotpaths pass1 summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061958337/read_hotpaths_pass2_summary.json](tmp/perf/ci-artifacts/run-23061958337/read_hotpaths_pass2_summary.json) | Historical performance/test/debug/bootstrap artifact: read hotpaths pass2 summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/ci-artifacts/run-23061958337/runtime_observability_summary.json](tmp/perf/ci-artifacts/run-23061958337/runtime_observability_summary.json) | Historical performance/test/debug/bootstrap artifact: runtime observability summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/explain_alerts.txt](tmp/perf/explain_alerts.txt) | Historical performance/test/debug/bootstrap artifact: explain alerts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/explain_alerts_after_opt.txt](tmp/perf/explain_alerts_after_opt.txt) | Historical performance/test/debug/bootstrap artifact: explain alerts after opt. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/explain_tx_date.txt](tmp/perf/explain_tx_date.txt) | Historical performance/test/debug/bootstrap artifact: explain tx date. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/explain_tx_search.txt](tmp/perf/explain_tx_search.txt) | Historical performance/test/debug/bootstrap artifact: explain tx search. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/explain_tx_search_108k_no_date.txt](tmp/perf/explain_tx_search_108k_no_date.txt) | Historical performance/test/debug/bootstrap artifact: explain tx search 108k no date. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/explain_tx_search_108k_with_date.txt](tmp/perf/explain_tx_search_108k_with_date.txt) | Historical performance/test/debug/bootstrap artifact: explain tx search 108k with date. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/explain_tx_search_after_trgm.txt](tmp/perf/explain_tx_search_after_trgm.txt) | Historical performance/test/debug/bootstrap artifact: explain tx search after trgm. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-many-org-dashboard.txt](tmp/perf/k6-many-org-dashboard.txt) | Historical performance/test/debug/bootstrap artifact: k6 many org dashboard. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-calibrated.env](tmp/perf/k6-mixed-calibrated.env) | Historical performance/test/debug/bootstrap artifact: k6 mixed calibrated. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-calibrated-after-rebuild-token-refresh.txt](tmp/perf/k6-mixed-churn-calibrated-after-rebuild-token-refresh.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn calibrated after rebuild token refresh. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-calibrated-after-rebuild.txt](tmp/perf/k6-mixed-churn-calibrated-after-rebuild.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn calibrated after rebuild. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-compare-rate12-afterfix.txt](tmp/perf/k6-mixed-churn-compare-rate12-afterfix.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn compare rate12 afterfix. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-compare-rate12.txt](tmp/perf/k6-mixed-churn-compare-rate12.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn compare rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-compare-window-afterfix.txt](tmp/perf/k6-mixed-churn-compare-window-afterfix.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn compare window afterfix. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-compare-window.txt](tmp/perf/k6-mixed-churn-compare-window.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn compare window. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rate10.txt](tmp/perf/k6-mixed-churn-rate10.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rate10. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rate12.txt](tmp/perf/k6-mixed-churn-rate12.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rate8.txt](tmp/perf/k6-mixed-churn-rate8.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rate8. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rerun-dbpool-rate12.txt](tmp/perf/k6-mixed-churn-rerun-dbpool-rate12.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rerun dbpool rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rerun-dbpool-window.txt](tmp/perf/k6-mixed-churn-rerun-dbpool-window.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rerun dbpool window. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rerun-rate12.txt](tmp/perf/k6-mixed-churn-rerun-rate12.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rerun rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rerun-tuned-rate12.txt](tmp/perf/k6-mixed-churn-rerun-tuned-rate12.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rerun tuned rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rerun-tuned-window.txt](tmp/perf/k6-mixed-churn-rerun-tuned-window.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rerun tuned window. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rerun-tuned2-rate12.txt](tmp/perf/k6-mixed-churn-rerun-tuned2-rate12.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rerun tuned2 rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rerun-tuned2-window.txt](tmp/perf/k6-mixed-churn-rerun-tuned2-window.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rerun tuned2 window. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rerun-tuned3-rate12.txt](tmp/perf/k6-mixed-churn-rerun-tuned3-rate12.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rerun tuned3 rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rerun-tuned3-window.txt](tmp/perf/k6-mixed-churn-rerun-tuned3-window.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rerun tuned3 window. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-rerun-window.txt](tmp/perf/k6-mixed-churn-rerun-window.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn rerun window. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-tuned-rate10.txt](tmp/perf/k6-mixed-churn-tuned-rate10.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn tuned rate10. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-tuned-rate12.txt](tmp/perf/k6-mixed-churn-tuned-rate12.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn tuned rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-tuned-rate8.txt](tmp/perf/k6-mixed-churn-tuned-rate8.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn tuned rate8. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-tuned-windows.txt](tmp/perf/k6-mixed-churn-tuned-windows.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn tuned windows. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn-windows.txt](tmp/perf/k6-mixed-churn-windows.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn windows. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-mixed-churn.txt](tmp/perf/k6-mixed-churn.txt) | Historical performance/test/debug/bootstrap artifact: k6 mixed churn. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-calibrated.env](tmp/perf/k6-read-calibrated.env) | Historical performance/test/debug/bootstrap artifact: k6 read calibrated. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-hotpaths-calibrated-after-rebuild.txt](tmp/perf/k6-read-hotpaths-calibrated-after-rebuild.txt) | Historical performance/test/debug/bootstrap artifact: k6 read hotpaths calibrated after rebuild. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-hotpaths-calibrated.txt](tmp/perf/k6-read-hotpaths-calibrated.txt) | Historical performance/test/debug/bootstrap artifact: k6 read hotpaths calibrated. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-hotpaths-rate12.txt](tmp/perf/k6-read-hotpaths-rate12.txt) | Historical performance/test/debug/bootstrap artifact: k6 read hotpaths rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-hotpaths-rate13.txt](tmp/perf/k6-read-hotpaths-rate13.txt) | Historical performance/test/debug/bootstrap artifact: k6 read hotpaths rate13. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-hotpaths-rate14.txt](tmp/perf/k6-read-hotpaths-rate14.txt) | Historical performance/test/debug/bootstrap artifact: k6 read hotpaths rate14. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-hotpaths-rate15.txt](tmp/perf/k6-read-hotpaths-rate15.txt) | Historical performance/test/debug/bootstrap artifact: k6 read hotpaths rate15. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-hotpaths.txt](tmp/perf/k6-read-hotpaths.txt) | Historical performance/test/debug/bootstrap artifact: k6 read hotpaths. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-rate12.env](tmp/perf/k6-read-rate12.env) | Historical performance/test/debug/bootstrap artifact: k6 read rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-rate13-baseline-after-opt.txt](tmp/perf/k6-read-rate13-baseline-after-opt.txt) | Historical performance/test/debug/bootstrap artifact: k6 read rate13 baseline after opt. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-rate13-baseline.env](tmp/perf/k6-read-rate13-baseline.env) | Historical performance/test/debug/bootstrap artifact: k6 read rate13 baseline. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-rate13-variant-a-after-opt.txt](tmp/perf/k6-read-rate13-variant-a-after-opt.txt) | Historical performance/test/debug/bootstrap artifact: k6 read rate13 variant a after opt. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-rate13-variant-a.env](tmp/perf/k6-read-rate13-variant-a.env) | Historical performance/test/debug/bootstrap artifact: k6 read rate13 variant a. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-rate13-variant-b-after-opt.txt](tmp/perf/k6-read-rate13-variant-b-after-opt.txt) | Historical performance/test/debug/bootstrap artifact: k6 read rate13 variant b after opt. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-rate13-variant-b.env](tmp/perf/k6-read-rate13-variant-b.env) | Historical performance/test/debug/bootstrap artifact: k6 read rate13 variant b. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-rate13.env](tmp/perf/k6-read-rate13.env) | Historical performance/test/debug/bootstrap artifact: k6 read rate13. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-rate14.env](tmp/perf/k6-read-rate14.env) | Historical performance/test/debug/bootstrap artifact: k6 read rate14. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read-rate15.env](tmp/perf/k6-read-rate15.env) | Historical performance/test/debug/bootstrap artifact: k6 read rate15. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-read.env](tmp/perf/k6-read.env) | Historical performance/test/debug/bootstrap artifact: k6 read. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-report-burst.txt](tmp/perf/k6-report-burst.txt) | Historical performance/test/debug/bootstrap artifact: k6 report burst. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-rerun-dbpool.env](tmp/perf/k6-rerun-dbpool.env) | Historical performance/test/debug/bootstrap artifact: k6 rerun dbpool. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-rerun-tuned.env](tmp/perf/k6-rerun-tuned.env) | Historical performance/test/debug/bootstrap artifact: k6 rerun tuned. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-rerun-tuned2.env](tmp/perf/k6-rerun-tuned2.env) | Historical performance/test/debug/bootstrap artifact: k6 rerun tuned2. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-rerun-tuned3.env](tmp/perf/k6-rerun-tuned3.env) | Historical performance/test/debug/bootstrap artifact: k6 rerun tuned3. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-rerun.env](tmp/perf/k6-rerun.env) | Historical performance/test/debug/bootstrap artifact: k6 rerun. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-write-calibrated.env](tmp/perf/k6-write-calibrated.env) | Historical performance/test/debug/bootstrap artifact: k6 write calibrated. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-write-heavy-calibrated-after-rebuild.txt](tmp/perf/k6-write-heavy-calibrated-after-rebuild.txt) | Historical performance/test/debug/bootstrap artifact: k6 write heavy calibrated after rebuild. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-write-heavy-rate12.txt](tmp/perf/k6-write-heavy-rate12.txt) | Historical performance/test/debug/bootstrap artifact: k6 write heavy rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/k6-write-rate12.env](tmp/perf/k6-write-rate12.env) | Historical performance/test/debug/bootstrap artifact: k6 write rate12. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/mock_gate_summary.json](tmp/perf/mock_gate_summary.json) | Historical performance/test/debug/bootstrap artifact: mock gate summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/mock_gate_summary.md](tmp/perf/mock_gate_summary.md) | Historical performance/test/debug/bootstrap artifact: mock gate summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/mock_summary.json](tmp/perf/mock_summary.json) | Historical performance/test/debug/bootstrap artifact: mock summary. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/perf_compare.json](tmp/perf/perf_compare.json) | Historical performance/test/debug/bootstrap artifact: perf compare. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/perf_compare_orgs.json](tmp/perf/perf_compare_orgs.json) | Historical performance/test/debug/bootstrap artifact: perf compare orgs. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/perf_compare_rerun.json](tmp/perf/perf_compare_rerun.json) | Historical performance/test/debug/bootstrap artifact: perf compare rerun. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/perf_multi.json](tmp/perf/perf_multi.json) | Historical performance/test/debug/bootstrap artifact: perf multi. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/perf_multi_tuned.json](tmp/perf/perf_multi_tuned.json) | Historical performance/test/debug/bootstrap artifact: perf multi tuned. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/perf_org_ids.json](tmp/perf/perf_org_ids.json) | Historical performance/test/debug/bootstrap artifact: perf org ids. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/perf_org_ids_tuned.json](tmp/perf/perf_org_ids_tuned.json) | Historical performance/test/debug/bootstrap artifact: perf org ids tuned. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/seed_index_pass.log](tmp/perf/seed_index_pass.log) | Historical performance/test/debug/bootstrap artifact: seed index pass. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/transactions_schema.txt](tmp/perf/transactions_schema.txt) | Historical performance/test/debug/bootstrap artifact: transactions schema. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/worker-compare-window-afterfix-ts.log](tmp/perf/worker-compare-window-afterfix-ts.log) | Historical performance/test/debug/bootstrap artifact: worker compare window afterfix ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/worker-compare-window-ts.log](tmp/perf/worker-compare-window-ts.log) | Historical performance/test/debug/bootstrap artifact: worker compare window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/worker-rerun-dbpool-window-ts.log](tmp/perf/worker-rerun-dbpool-window-ts.log) | Historical performance/test/debug/bootstrap artifact: worker rerun dbpool window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/worker-rerun-tuned-window-ts.log](tmp/perf/worker-rerun-tuned-window-ts.log) | Historical performance/test/debug/bootstrap artifact: worker rerun tuned window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/worker-rerun-tuned2-window-ts.log](tmp/perf/worker-rerun-tuned2-window-ts.log) | Historical performance/test/debug/bootstrap artifact: worker rerun tuned2 window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/worker-rerun-tuned3-window-ts.log](tmp/perf/worker-rerun-tuned3-window-ts.log) | Historical performance/test/debug/bootstrap artifact: worker rerun tuned3 window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/worker-rerun-window-ts.log](tmp/perf/worker-rerun-window-ts.log) | Historical performance/test/debug/bootstrap artifact: worker rerun window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/worker-tuned-window-ts.log](tmp/perf/worker-tuned-window-ts.log) | Historical performance/test/debug/bootstrap artifact: worker tuned window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/worker-window-ts.log](tmp/perf/worker-window-ts.log) | Historical performance/test/debug/bootstrap artifact: worker window ts. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf/worker-window.log](tmp/perf/worker-window.log) | Historical performance/test/debug/bootstrap artifact: worker window. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf_bootstrap.json](tmp/perf_bootstrap.json) | Historical performance/test/debug/bootstrap artifact: perf bootstrap. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf_bootstrap_utf8.json](tmp/perf_bootstrap_utf8.json) | Historical performance/test/debug/bootstrap artifact: perf bootstrap utf8. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf_org_ids.json](tmp/perf_org_ids.json) | Historical performance/test/debug/bootstrap artifact: perf org ids. Not fresh verification; payload may contain disposable identities/tokens. |
| [tmp/perf_org_ids_utf8.json](tmp/perf_org_ids_utf8.json) | Historical performance/test/debug/bootstrap artifact: perf org ids utf8. Not fresh verification; payload may contain disposable identities/tokens. |

#### worker files

| File | Responsibility |
| --- | --- |
| [worker/Dockerfile](worker/Dockerfile) | Container build/entrypoint for worker. |
| [worker/README.md](worker/README.md) | Worker Service. Sections: Responsibilities; Local usage. Historical/current guidance or proposals; compare with source. |

#### Local environment and working-tree state

Private `.env`/`.env.production` values are not public documentation. `.env.cookie` is staged in this workspace and is listed by filename only; this task preserves it. The existing README changes are updated in place. Generated package metadata, runtime PID/log helpers, temporary load environments and reports may be tracked but are not application implementation. Review their retention/secret hygiene separately.

### I. Research coverage and verification boundaries

- Source snapshot: **`66ac1e7`**, inspected September 15, 2026; includes current working-tree/index files.
- Tracked files catalogued: **957**.
- Registered HTTP routes: **185**.
- Leaf route modules: **29**.
- Backend Settings variables: **91**.
- Mapped table classes: **64**.
- Schema classes: **208**.
- Alembic revisions: **40**.
- Backend test files: **109**.
- All current Python source files were parsed and inventoried; frontend source, provider/configuration declarations and current/historical documents were re-evaluated. Private env values and historical log/bootstrap payloads were not reproduced.
- Documentation verification checks current route coverage, settings/model/schema/migration counts, tracked-file catalog coverage, links, contents anchors, code fences and Git whitespace. Application tests, migrations, paid/live providers, browser suites and load tests are separate runtime verification steps.
