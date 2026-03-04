# ADR 0004: Report idempotency

## Decision
Weekly reports are idempotent by unique key `(org_id, week_start)` and deterministic S3 key.

## Why
- Prevent duplicate reports on retries.
- Safe Celery retry behavior.

## Implementation
- DB unique constraint `uq_report_org_week`.
- Task checks for existing report before generate/upload.
- Storage key: `reports/{org_id}/{week_start}.pdf`.
