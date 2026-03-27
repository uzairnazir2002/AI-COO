# Privacy and Deletion Operations

## Owner UI controls
- `Settings -> Data & compliance actions`
  - Request account deletion
  - Request organization deletion (owner + explicit `DELETE` confirmation)
- `Activity -> Security & compliance`
  - Audit NDJSON export (`/api/v1/admin/audit/export`)
  - PII rotation (`/api/v1/admin/security/rotate-pii`)
  - Deletion request lifecycle visibility (`PENDING` / `PROCESSED`, `delete_after`, `processed_at`)

## Deletion lifecycle
- Deletion requests are stored in `deletion_requests`.
- Requests start in `PENDING` and are processed by scheduled worker purge job:
  - task: `app.jobs.tasks.privacy.purge_deletion_requests`
  - beat schedule key: `deletion-purge`
- Purge outcomes are reflected by:
  - `status` and `processed_at` on deletion request records
  - audit events (`auth.delete.purged`, `org.delete.purged`)

## CI migration safety gate
- Workflow: `.github/workflows/ci.yml`
- Gate executes:
  - `alembic upgrade head`
  - `alembic downgrade -1`
  - `alembic upgrade head`
- This protects release pipelines from migration drift/regression.
