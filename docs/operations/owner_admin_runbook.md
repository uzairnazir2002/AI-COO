# Owner/Admin Operations Runbook

Date: 2026-03-25

## Scope
- Owner/admin operational workflows in Activity and Settings pages.
- Session/auth recovery behavior for frontend/API failures.
- DLQ replay, outbox retry, scheduler controls, audit export, and PII/deletion operations.

## Frontend auth/network behavior
- Global API event handling is centralized in:
  - `frontend/src/lib/api/client.ts`
  - `frontend/src/components/common/global-api-feedback.tsx`
- Effects:
  - Expired auth (`401`) triggers one global session-expired flow and redirect to login with `return_to`.
  - Network/CORS failures trigger one global degraded-connectivity warning toast.

## Owner diagnostics panel (Activity)
- Page: `/app/activity`
- Sections:
  - Runtime SLOs
  - Runtime metrics (`queue_depth_active`, `queue_lag_seconds`, `dead_letter_open`, `worker_health`)
  - Outbox monitor and retry controls
  - Dead-letter queue list + replay/dismiss
  - Scheduler controls (`pause`, `resume`, `run now`)

## DLQ triage procedure
1. Open Activity → Operational diagnostics.
2. Filter dead-letter rows to `OPEN`.
3. Inspect `source_type`, `source_name`, `last_error`, `attempts`.
4. Replay when root cause is resolved:
   - `POST /api/v1/admin/dead-letter/{id}/replay?org_id=...`
5. Dismiss only for accepted/non-actionable failures:
   - `POST /api/v1/admin/dead-letter/{id}/dismiss?org_id=...&reason=...`
6. Confirm:
   - `dead_letter_open` decreases
   - `worker_health` returns to `ok`

## Outbox retry procedure
1. Activity → Outbox monitor, filter `FAILED`/`RETRYING`.
2. Trigger retry:
   - `POST /api/v1/admin/outbox/{event_id}/retry?org_id=...`
3. Verify transition from `PENDING/RETRYING` to `SENT`.

## Queue lag / worker health procedure
1. Check runtime metrics:
   - `GET /api/v1/admin/runtime-metrics?org_id=...`
2. If `queue_lag_breach=true`:
   - inspect active jobs and outbox backlog in Activity
   - run critical schedules manually if required
   - verify DB connection pressure (`db_active_connections`)
3. If persistent, scale worker/API resources and re-check lag.

## Security/compliance procedures
- Audit export:
  - `GET /api/v1/admin/audit/export?org_id=...&since=...&until=...`
- PII rotation:
  - `POST /api/v1/admin/security/rotate-pii?org_id=...`
- Deletion request visibility:
  - `GET /api/v1/admin/deletion-requests?org_id=...`

## Post-incident verification
- Confirm no open critical dead-letter events.
- Confirm runtime SLO breaches are cleared.
- Confirm notification stream and dashboard data are current.

## Alert freshness triggers (budget/import writes)
- Alert recompute is auto-enqueued on:
  - transaction create/update/delete (`POST/PUT/DELETE /api/v1/transactions`)
  - transaction bulk category remap (`POST /api/v1/transactions/bulk/remap-category`)
  - budget create/update (`POST /api/v1/budgets`, `PUT /api/v1/budgets/{id}`)
  - committed CSV import (`POST /api/v1/transactions/import/csv` with `commit=true`)
- Enqueue behavior is dedupe-safe via `alerts:{org_id}` tracked job key.
- Audit trail event:
  - `alert.recalc.enqueue` with source metadata (`transaction.*`, `budget.*`, `transaction.import_csv`).
