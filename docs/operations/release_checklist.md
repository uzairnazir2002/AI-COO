# Release Checklist (Strict Go/No-Go)

Date: 2026-03-27  
Owner: Release Manager / Tech Lead

## 1. Pre-Release Preconditions

- [ ] Target commit SHA is frozen and tagged in release notes.
- [ ] No unreviewed hotfix commits remain on release branch.
- [ ] All required runtime secrets are provisioned in environment/secret manager (not repo files).
- [ ] Deployment window, rollback owner, and communication channel are assigned.

## 2. Security and Secret Hygiene

- [ ] `secret-hygiene` CI job is green for target SHA.
- [ ] Exposed/legacy credentials are rotated (DB, Redis, JWT, provider keys, webhook secrets).
- [ ] `.env` and `.env.production` do not contain real production secrets.
- [ ] Secret injection path is validated in runtime platform (Kubernetes/Compose/host env).
- [ ] PII rotation endpoint health is verified:
  - `POST /api/v1/admin/security/rotate-pii?org_id=...` (owner only, staging check at minimum).

## 3. CI Gate Matrix (Must Be Green)

- [ ] `backend`
- [ ] `frontend`
- [ ] `migration-safety`
- [ ] `precommit`
- [ ] `secret-hygiene`

Env-gated suites (required for full production candidate):
- [ ] `playwright-cookie-csrf`
- [ ] `playwright-sse-fallback`
- [ ] `playwright-visual`
- [ ] `plaid-epic-a` (if Plaid is enabled for target environment)
- [ ] `ai-live-mode` (if `AI_PROVIDER=openai` for target environment)

## 4. Database and Migration Safety

- [ ] Alembic upgrade from current prod version to target passes.
- [ ] Alembic downgrade smoke path verified in CI (`migration-safety`).
- [ ] Post-migration schema sanity checks pass (critical tables/indexes present).

## 5. AI Live-Mode Readiness (When Enabled)

- [ ] `AI_PROVIDER=openai` configured in staging/prod as intended.
- [ ] `GET /api/v1/ai/health` returns healthy provider state.
- [ ] Live-mode verification script passes:
  - `python scripts/ops/verify_ai_live_mode.py --api-base-url <url>/api/v1 --database-url <db_url> --live-check --verify-fallback-test --fallback-test-path backend/app/tests/test_ai_service.py::test_ai_service_falls_back_on_provider_error`
- [ ] Fallback path behavior confirmed (provider failure still yields deterministic summary).

## 6. Performance and Scalability Gates

- [ ] Perf workflow is green on target SHA (`.github/workflows/perf.yml`).
- [ ] Split read gate passes at configured guardrail (`RATE=13`, runtime metrics disabled in hotpath profile).
- [ ] Runtime observability profile passes (`RATE=2`).
- [ ] Inventory churn profile reviewed; no unacceptable regression vs prior baseline.
- [ ] `perf-artifacts/perf_gate_summary.json` and `perf_gate_summary.md` archived with release evidence.

## 7. Operational Readiness

- [ ] Owner/admin runbook reviewed: `docs/operations/owner_admin_runbook.md`
- [ ] Worker/DLQ runbook reviewed: `docs/operations/worker_resilience.md`
- [ ] Backup/restore runbook reviewed: `docs/operations/backup_restore.md`
- [ ] On-call responder acknowledges rollback steps and escalation contacts.

## 8. Deployment Execution

- [ ] Deploy backend + worker + frontend with target SHA.
- [ ] Verify service health endpoints post-deploy.
- [ ] Confirm async workers are processing queues (no abnormal lag/dead letters).
- [ ] Confirm billing/integrations webhooks are reachable and signature checks are passing.

## 9. Post-Deploy Verification

- [ ] Smoke test critical flows:
  - auth/login/session refresh
  - transaction create/import
  - dashboard + alerts
  - report generate/download
  - AI summary/chat endpoint
- [ ] Activity page shows healthy runtime SLOs and no critical DLQ accumulation.
- [ ] Audit export path is functioning for owner role.

## 10. Rollback Criteria and Trigger

Immediate rollback if any of the following occurs:
- [ ] sustained auth failures or token/session breakage
- [ ] data corruption or migration incompatibility
- [ ] queue lag breach with user-visible failures
- [ ] persistent 5xx increase beyond agreed SLO budget

Rollback execution:
- [ ] revert to previous release artifact/image tag
- [ ] run rollback migration (if required by change plan)
- [ ] confirm health and smoke tests on reverted version

## 11. Final Sign-Off

- [ ] Engineering lead sign-off
- [ ] Product owner sign-off
- [ ] Operations/on-call sign-off
- [ ] Release evidence package stored (CI links, perf artifacts, runbook checklist, incident notes)

