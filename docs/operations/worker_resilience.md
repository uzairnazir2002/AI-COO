# Worker Resilience and DLQ Operations

## Scope
- Dead-letter queue visibility for terminal worker failures (`JOB` and `OUTBOX` sources).
- Owner replay and dismiss controls for dead-letter entries.
- Runtime lag/health signals in `/api/v1/admin/runtime-metrics`.

## Signals
- `queue_depth_active`: active org-scoped jobs (`PENDING`/`RUNNING`/`RETRYING`).
- `queue_lag_seconds`: age of the oldest active job.
- `queue_lag_breach`: `true` when lag exceeds `RUNTIME_QUEUE_LAG_THRESHOLD_SECONDS` (default `180`).
- `dead_letter_open`: count of open dead-letter records.
- `worker_health`: `degraded` when lag breach exists or open dead-letter count > 0.

## Dead-letter API
- `GET /api/v1/admin/dead-letter?org_id=...`
- `POST /api/v1/admin/dead-letter/{id}/replay?org_id=...`
- `POST /api/v1/admin/dead-letter/{id}/dismiss?org_id=...&reason=...`

## Operator Flow
1. Open Activity → Operational diagnostics.
2. Filter dead-letter rows by `OPEN`.
3. Use `Replay` to re-dispatch supported sources.
4. Use `Dismiss` for acknowledged non-actionable failures.
5. Confirm `dead_letter_open` and `queue_lag_breach` return to healthy values.
