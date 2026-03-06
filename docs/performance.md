# Performance Harness

This repository includes a repeatable load-test harness for core API paths.

## Goals
- Verify dashboard and list endpoints stay within MVP latency budgets.
- Catch regressions in CI via k6 thresholds.
- Seed realistic high-volume transaction data.

## Seed dataset
Script: `scripts/seed_load_dataset.py`

Example:
```bash
python scripts/seed_load_dataset.py \
  --org-id <ORG_ID> \
  --created-by <USER_ID> \
  --months 12 \
  --rows 50000
```

Notes:
- Supports large loads (50k-200k rows).
- Recomputes monthly aggregates after insert.
- Uses deterministic RNG via `--seed`.

## Bootstrap auth/org
Script: `scripts/loadtest/bootstrap_perf.py`

This creates:
- one user
- one org
- bearer token

And prints JSON with `access_token`, `org_id`, `user_id`, and date range values.

## k6 scenario
Script: `scripts/loadtest/k6-smoke.js`

Exercised endpoints:
- `GET /analytics/summary`
- `GET /analytics/cashflow`
- `GET /transactions`
- `POST /ai/summary`

Thresholds:
- `p95 < 2000ms` for summary/cashflow/transactions
- `p95 < 3000ms` for ai summary
- failure rate `< 1%`

## CI workflow
Workflow: `.github/workflows/perf.yml`

What it does:
1. boots docker stack
2. bootstraps test org/user/token
3. seeds 5k-row CI dataset
4. runs k6 smoke profile
5. fails on threshold regressions

For deeper tests, run locally with a larger seed size (50k+ rows).
