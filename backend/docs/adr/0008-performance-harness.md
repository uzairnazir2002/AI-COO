# ADR 0008: Performance Seed + Load Harness

## Status
Accepted

## Context
We needed repeatable evidence that dashboard and transaction endpoints stay within MVP latency budgets under realistic volume.

## Decision
- Add deterministic seed generator: `scripts/seed_load_dataset.py` (supports 50k-200k+ rows).
- Add k6 smoke profile: `scripts/loadtest/k6-smoke.js` for:
  - summary
  - cashflow
  - transactions list
  - ai summary
- Add CI workflow: `.github/workflows/perf.yml`:
  - boot stack
  - bootstrap auth/org
  - seed CI dataset
  - run k6 with p95 thresholds.

## Consequences
- Pros:
  - objective regression guardrails.
  - repeatable load setup for local and CI.
- Cons:
  - extra CI runtime and infra boot cost.
