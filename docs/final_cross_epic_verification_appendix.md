# Final Cross-Epic Verification Appendix

Date: 2026-03-26

## 1) Backend full regression
- Command:
  - `.\.venv\Scripts\python.exe -m pytest backend/app/tests -q`
- Result:
  - `221 passed, 4 skipped in 27.93s`

## 2) Frontend production build
- Command:
  - `npm run build` (from `frontend/`)
- Result:
  - Success (`Next.js 15.5.12`)
  - Includes routes for `/app/assistant`, `/app/budgets`, `/app/inventory`, `/app/settings`, `/app/alerts`, `/app/reports`.

## 3) Full Playwright run (latest)
- Command:
  - `E2E_BASE_URL=http://localhost:3000 E2E_API_URL=http://localhost:8000/api/v1 npx playwright test --reporter=json > playwright-report-full.json`
- Stats:
  - `expected=19`
  - `skipped=9`
  - `unexpected=0`
  - `flaky=0`

### Spec matrix
| Spec | Status | Notes |
|---|---|---|
| `e2e/ai-chat.spec.ts` | PASS | Chat session + grounded/fallback indicator |
| `e2e/alert-refresh-queue.spec.ts` | PASS | Queue signal + activity + alert persistence |
| `e2e/budgets.spec.ts` | PASS | Budget CRUD/variance flow |
| `e2e/cookie-csrf.spec.ts` | SKIP | Env-gated |
| `e2e/dashboard-budget-variance.spec.ts` | PASS | Dashboard variance panels |
| `e2e/full-flow.spec.ts` | PASS | End-to-end app path (auth -> dashboard -> transactions -> reports) |
| `e2e/inventory-alerts.spec.ts` | PASS | Inventory mutation to persisted stockout alert |
| `e2e/mfa-session.spec.ts` | PASS | MFA/session flow |
| `e2e/ops-flow.spec.ts` | PASS | Ops/auth/settings flow |
| `e2e/plaid-integration.spec.ts` | SKIP | Env-gated (`E2E_PLAID_SANDBOX`) |
| `e2e/polish.spec.ts` | PASS | CSV mapping/bulk remap/forecast override/RBAC polish checks |
| `e2e/sse-fallback.spec.ts` | SKIP | Env-gated |
| `e2e/stripe-integration.spec.ts` | PASS | Live signed webhook -> reconciliation |
| `e2e/visual.spec.ts` | SKIP | Visual mode-gated (`E2E_VISUAL=1`) |

## 4) Perf gate and load artifacts
Artifacts folder:
- `perf-artifacts/stage2-closure/`

### Gate summary
- Source:
  - `perf-artifacts/stage2-closure/perf_gate_summary.json`
  - `perf-artifacts/stage2-closure/perf_gate_summary.md`
- Gate result:
  - `PASS`

### Key guardrail metrics
- Read hotpaths pass 1 p95 (ms):
  - summary `89.25`
  - cashflow `84.60`
  - transactions `83.20`
  - alerts `82.73`
  - failure rate `0.0000`, dropped iterations `0`
- Read hotpaths pass 2 p95 (ms):
  - summary `70.08`
  - cashflow `70.54`
  - transactions `68.55`
  - alerts `64.51`
  - failure rate `0.0000`, dropped iterations `0`
- Runtime observability p95 (ms):
  - runtime metrics `56.56`
  - failure rate `0.0000`, dropped iterations `0`

### Additional high-churn observations (non-gating)
- `inventory_churn_summary.json` shows elevated latency/failures and dropped iterations at the executed high-rate envelope.
- `mixed_churn_summary.json` shows non-zero dropped iterations under churn pressure.
- These are tracked as residual capacity/perf hardening tasks, not current guardrail gate failures.
