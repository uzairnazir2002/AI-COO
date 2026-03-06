# ADR 0005: Job State Standardization

## Status
Accepted

## Context
Background tasks were tracked inconsistently. Some tasks wrote `JobState` directly with a `DONE` terminal status while others had no retry/error metadata. This made production triage and tenant-safe operations difficult.

## Decision
- Keep `job_states` as the canonical task tracking table.
- Standardize lifecycle statuses:
  - `PENDING`
  - `RUNNING`
  - `RETRYING`
  - `SUCCEEDED`
  - `FAILED`
- Expand `job_states` with operational metadata:
  - `org_id`, `task_id`, `task_name`
  - `progress`
  - `request_id`, `correlation_id`
  - `last_error`, `traceback_summary`
  - `retry_count`, `last_retry_at`
  - `created_at`, `updated_at`
- All Celery tasks use shared task tracking helpers to ensure uniform behavior.
- Add `/api/v1/jobs` endpoint for org-scoped job visibility with pagination/filtering.
- Redact sensitive error fields for `VIEWER` role responses.

## Consequences
- Pros:
  - Reliable, uniform job observability.
  - Better incident response (retry/failure context).
  - Tenant-safe job introspection.
- Cons:
  - Slightly larger task write volume due to state transitions.
  - Additional schema complexity in `job_states`.
