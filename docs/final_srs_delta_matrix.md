# Final SRS Delta Matrix (Current Snapshot)

Date: 2026-03-26

Status legend: `COMPLETE`, `PARTIAL`, `MISSING`

| Requirement | Status | Evidence | Residual risk / note |
|---|---|---|---|
| FR-1 Registration | COMPLETE | `backend/app/api/v1/auth.py`, `backend/app/domain/services/auth_service.py`, `backend/app/tests/test_auth_delete_account_endpoint.py` | Local seeded users can still cause expected 409 in manual testing if re-registered |
| FR-2 Login + refresh | COMPLETE | `backend/app/api/v1/auth.py`, `backend/app/core/security.py`, `backend/app/tests/test_security_tokens.py`, `backend/app/tests/test_auth_lockout_endpoint.py` | Lockout telemetry depends on Redis availability |
| FR-3 RBAC | COMPLETE | `backend/app/api/deps.py`, `backend/app/api/v1/organizations.py`, `backend/app/tests/test_tenant_isolation.py`, `backend/app/tests/test_owner_policy_deps.py` | None |
| FR-4 Create organization | COMPLETE | `backend/app/api/v1/organizations.py`, `backend/app/domain/services/org_service.py` | None |
| FR-5 Transactions CRUD + audit | COMPLETE | `backend/app/api/v1/transactions.py`, `backend/app/domain/services/transaction_service.py`, `backend/app/domain/repos/audit_repo.py` | None |
| FR-6 CSV import + mapping + dedupe + profiles | COMPLETE | `backend/app/utils/csv_import.py`, `backend/app/api/v1/transactions.py`, `backend/app/tests/test_csv_import.py`, `backend/app/tests/test_import_profiles_endpoint.py` | Import quality depends on mapping profile hygiene |
| FR-7 Dashboard financial summary | COMPLETE | `backend/app/api/v1/analytics.py`, `backend/app/domain/services/analytics_service.py`, `backend/app/tests/test_analytics.py` | None |
| FR-8 Runway calculator | COMPLETE | `backend/app/api/v1/runway.py`, `backend/app/tests/test_runway.py` | None |
| FR-9 Forecasting (scenarios) | COMPLETE | `backend/app/domain/services/analytics_service.py`, `backend/app/api/v1/analytics.py`, `backend/app/tests/test_analytics.py` | Forecast quality is model/assumption sensitive |
| FR-10 Anomaly detection | COMPLETE | `backend/app/domain/services/alerts_service.py`, `backend/app/tests/test_alerts_ordering.py` | Threshold tuning may need production calibration |
| FR-11 Profit leak detection | COMPLETE | `backend/app/domain/services/alerts_service.py`, `backend/app/tests/test_alerts_ordering.py` | Signal sensitivity tuning may evolve |
| FR-12 Weekly reports (async, idempotent) | COMPLETE | `backend/app/api/v1/reports.py`, `backend/app/jobs/tasks/reports.py`, `backend/app/tests/test_reports_endpoint.py`, `backend/app/tests/test_reports_task.py` | None |
| FR-13 AI summary grounded + fallback | COMPLETE | `backend/app/domain/services/ai_service.py`, `backend/app/tests/test_ai_service.py`, `backend/app/tests/test_ai_chat_service.py` | LLM output remains provider-dependent; validator mitigates unsupported claims |
| NFR Security | COMPLETE | MFA/session/policy/lockout/privacy baseline in `backend/app/api/v1/auth.py`, `backend/app/core/mfa.py`, `backend/app/core/auth_lockout.py`, `backend/app/core/pii_crypto.py` | Key rotation operations require disciplined ops runbook execution |
| NFR Performance | PARTIAL | `perf-artifacts/stage2-closure/perf_gate_summary.json` (`PASS`), `scripts/loadtest/*`, `.github/workflows/perf.yml` | Inventory/mixed churn high-rate envelopes still show dropped iterations/latency pressure |
| NFR Scalability | PARTIAL | Split load profiles + seed tooling: `scripts/loadtest/`, `scripts/seed_load_dataset.py`, `docs/performance.md` | Need higher-envelope capacity tuning for sustained churn scenarios |
| NFR Reliability | COMPLETE | Backend full tests green (`221 passed, 4 skipped`), full Playwright regression green (`expected=19`, `unexpected=0`), async jobs/outbox/DLQ in place, strict release gate in `docs/operations/release_checklist.md` | Env-gated suites still require dedicated runs with required secrets/flags |

## Stage-2 epic completion rollup
- Epic A (Plaid): Implemented, env-gated e2e in full suite.
- Epic B (Stripe): Implemented and regression-covered.
- Epic C (Budgets): Implemented and regression-covered.
- Epic D (Multi-location): Implemented and regression-covered.
- Epic E (Inventory): Implemented; high-rate churn perf envelope still needs tuning.
- Epic F (AI Chat): Implemented with grounding/fallback indicator and e2e.

See:
- `docs/final_cross_epic_closure_matrix.md`
- `docs/final_cross_epic_verification_appendix.md`
- `docs/operations/release_checklist.md`
