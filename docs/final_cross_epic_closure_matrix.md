# Final Cross-Epic Closure Matrix (Stage-2 A-F)

Date: 2026-03-26

## Overall verdict
- Cross-epic implementation coverage is broadly complete across A-F.
- Formal closure is **COMPLETE** for the current regression gate: full Playwright run is green (`unexpected=0`).

## Matrix

| Epic | Target scope | Implementation status | Verification status | Evidence | Closure blocker |
|---|---|---|---|---|---|
| Epic A (Plaid) | Link token, exchange, connections, revoke, sync, webhook | COMPLETE | PARTIAL (env-gated e2e skipped in full suite) | `docs/epic_a_closure_delta.md`, `backend/app/api/v1/integrations.py`, `backend/app/domain/services/bank_integration_service.py`, `frontend/src/app/app/settings/page.tsx`, `backend/app/tests/test_integrations_webhook.py`, `backend/app/tests/test_plaid_sandbox_live.py` | `e2e/plaid-integration.spec.ts` skipped without sandbox env in full regression |
| Epic B (Stripe) | Connect, webhook ingestion, reconciliation, settings UX | COMPLETE | COMPLETE | `docs/epic_b_closure_delta.md`, `backend/app/api/v1/integrations.py`, `backend/app/domain/services/payment_integration_service.py`, `frontend/src/app/app/settings/page.tsx`, `backend/app/tests/test_integrations_payments_webhook.py`, `backend/app/tests/test_stripe_sandbox_live.py`, `frontend/e2e/stripe-integration.spec.ts` | None |
| Epic C (Budgets) | Budgets CRUD, variance analytics, alert refresh signaling, persisted threshold visibility | COMPLETE | COMPLETE | `docs/epic_c_closure_delta.md`, `backend/app/api/v1/budgets.py`, `backend/app/tests/test_budgets_endpoint.py`, `backend/app/tests/test_alerts_budget_threshold.py`, `frontend/e2e/budgets.spec.ts`, `frontend/e2e/alert-refresh-queue.spec.ts` | None |
| Epic D (Multi-location) | Locations module, location-aware alerts/filtering, benchmark API/dashboard, CSV location mapping | COMPLETE | COMPLETE | `docs/epic_d_closure_delta.md`, `docs/epic_d_location_delta.md`, `backend/app/api/v1/locations.py`, `backend/app/api/v1/analytics.py`, `backend/app/tests/test_locations_endpoint.py`, `backend/app/tests/test_analytics_location_benchmark_endpoint.py` | None |
| Epic E (Inventory) | Inventory domain/API, forecast, persisted stockout alerts, inventory UX | COMPLETE | COMPLETE (functional), PARTIAL (high-rate perf envelope) | `docs/epic_e_inventory_delta.md`, `backend/app/api/v1/inventory.py`, `backend/app/domain/services/inventory_service.py`, `backend/app/tests/test_inventory_endpoint.py`, `backend/app/tests/test_alerts_inventory_stockout.py`, `frontend/e2e/inventory-alerts.spec.ts`, `scripts/loadtest/k6-inventory-churn.js` | `inventory_churn` high-rate run shows latency/failure pressure and dropped iterations |
| Epic F (AI Chat) | Sessioned org-scoped chat, grounding reuse, fallback indicator, chat UI | COMPLETE | COMPLETE | `docs/epic_f_backend_delta.md`, `backend/app/api/v1/ai.py`, `backend/app/domain/services/ai_chat_service.py`, `backend/app/tests/test_ai_chat_endpoint.py`, `frontend/src/app/app/assistant/page.tsx`, `frontend/e2e/ai-chat.spec.ts` | None |

## Cross-epic regression status
- Backend full tests: **PASS** (`221 passed, 4 skipped`)
- Frontend production build: **PASS** (`Next.js 15.5.12`)
- Full Playwright suite: **PASS** (`expected=19`, `unexpected=0`, `skipped=9`)
- Perf gate (read/runtime profiles): **PASS**

## Remaining non-blocking hardening
1. Keep env-gated suites (`plaid-integration`, `cookie-csrf`, `sse-fallback`, `visual`) in dedicated scheduled/secret-enabled jobs.
2. Re-run inventory churn profile at agreed envelope and tighten Epic E capacity guardrail thresholds as load grows.
