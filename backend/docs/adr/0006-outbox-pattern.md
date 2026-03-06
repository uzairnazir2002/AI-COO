# ADR 0006: Outbox Pattern For Notifications

## Status
Accepted

## Context
Report generation and invite flows could commit business state successfully while notification delivery was still vulnerable to worker/process failures.

## Decision
- Add `outbox_events` table.
- Write outbox events in the same DB transaction as report/invite state changes.
- Consume outbox asynchronously via Celery (`process_outbox` beat task).
- Delivery state machine:
  - `PENDING` -> `PROCESSING` -> `SENT`
  - failures: `RETRYING` (with backoff) -> `FAILED` after max attempts.
- Add dedupe key support for idempotent notification emission.

## Consequences
- Pros:
  - no notification loss on app/worker crashes between commit and dispatch.
  - clear delivery observability and retry behavior.
- Cons:
  - extra DB writes and a periodic consumer job.
