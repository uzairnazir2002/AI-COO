# ADR 0001: Worker choice

## Decision
Use Celery + Redis broker with Celery Beat.

## Why
- Mature retry/backoff and scheduling features.
- Clear horizontal scaling path.
- Fits periodic weekly reporting and recomputation jobs.

## Consequences
- Redis must be available for enqueue/dequeue.
- Tasks must remain idempotent and side-effect-safe.
