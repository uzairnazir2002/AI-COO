# Performance Harness

This repository includes a repeatable load-test harness for core API paths.

## Goals
- Verify dashboard and list endpoints stay within MVP latency budgets.
- Catch regressions in CI via k6 thresholds.
- Seed realistic high-volume transaction data across single-org and many-org topologies.
- Exercise concurrency/churn paths for reports, alerts, and mixed import/read traffic.

## Seed dataset
Script: `scripts/seed_load_dataset.py`

Single org example (100k transactions):
```bash
python scripts/seed_load_dataset.py \
  --org-id <ORG_ID> \
  --created-by <USER_ID> \
  --months 12 \
  --rows 100000
```

Many-org example (100 orgs x 10k each):
```bash
python scripts/seed_load_dataset.py \
  --org-ids-file perf_org_ids.json \
  --created-by <USER_ID> \
  --months 12 \
  --rows 10000
```

Notes:
- Supports multiple org IDs using repeated `--org-id` or `--org-ids-file`.
- Supports large loads (50k-200k rows per org).
- Recomputes monthly aggregates after insert.
- Uses deterministic RNG via `--seed`.

## Bootstrap auth/org
Script: `scripts/loadtest/bootstrap_perf.py`

This creates:
- one user
- one org
- bearer token

And prints JSON with `access_token`, `org_id`, `user_id`, and date range values.

Script: `scripts/loadtest/bootstrap_multi_org_perf.py`

This creates:
- one user
- many orgs (`--org-count`)
- single bearer token valid for all created orgs

And prints JSON with `access_token`, `org_ids`, `user_id`, and date range values.

## k6 profiles
### 1) CI smoke profile
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

### 2) Many-org dashboard reads
Script: `scripts/loadtest/k6-many-org-dashboard.js`

Purpose:
- concurrent dashboard-style reads spread across many organizations.

Exercised endpoints:
- `GET /analytics/summary`
- `GET /analytics/cashflow`
- `GET /runway`
- `GET /alerts`

### 3) Report burst generation
Script: `scripts/loadtest/k6-report-burst.js`

Purpose:
- burst concurrency against async report enqueue flow and job list reads.

Exercised endpoints:
- `POST /reports/generate`
- `GET /jobs?task_name=generate_weekly_report`

### 4) Mixed churn profile
Script: `scripts/loadtest/k6-mixed-churn.js`

Purpose:
- mixed read/write + background job churn under sustained load.

Exercised endpoints:
- `GET /transactions`
- `GET /alerts`
- `POST /analytics/recompute`
- `POST /reports/generate`
- `POST /transactions/import/csv` (preview mode)

### 5) Read-only hotpaths profile
Script: `scripts/loadtest/k6-read-hotpaths.js`

Purpose:
- isolate dashboard/read latency under sustained concurrent reads.
- user-facing read SLO guardrail profile (`RATE=13` default).

Exercised endpoints:
- `GET /analytics/summary`
- `GET /analytics/cashflow`
- `GET /transactions`
- `GET /alerts`

Runtime-metrics sampling controls:
- `RUNTIME_METRICS_ENABLED` (`true|false`, default `false`)
- `RUNTIME_METRICS_EVERY_N` (default `1`; sample once every N iterations)

### 6) Write-heavy profile
Script: `scripts/loadtest/k6-write-heavy.js`

Purpose:
- isolate write + enqueue pressure without mixed-profile ambiguity.

Exercised endpoints:
- `POST /analytics/recompute`
- `POST /reports/generate`
- `POST /transactions/import/csv` (preview mode)
- `GET /admin/runtime-metrics`

Tracked custom gauges:
- `runtime_queue_depth`
- `runtime_db_active_connections`

### 7) Runtime observability profile (out-of-band)
Script: `scripts/loadtest/k6-runtime-observability.js`

Purpose:
- collect `/admin/runtime-metrics` without adding contention to user-facing read profiles.

Exercised endpoints:
- `GET /admin/runtime-metrics`

Tracked custom gauges:
- `runtime_queue_depth`
- `runtime_db_active_connections`

### 8) Perf gate evaluator
Script: `scripts/loadtest/evaluate_perf_gates.py`

Config:
- `scripts/loadtest/slo_guardrails.json`

Gate behavior:
- Read profile is run twice at `RATE=13` with `RUNTIME_METRICS_ENABLED=false`.
- Build fails only if read SLO breaches occur in both consecutive passes.
- Runtime observability profile (`RATE=2`) is evaluated out-of-band and still gates on its own SLO.

## Local scalability runbook
1. Bootstrap many-org fixture:
```bash
python scripts/loadtest/bootstrap_multi_org_perf.py --org-count 100 > perf_multi.json
```
2. Export vars:
```bash
export ACCESS_TOKEN=$(python -c 'import json;print(json.load(open("perf_multi.json"))["access_token"])')
export USER_ID=$(python -c 'import json;print(json.load(open("perf_multi.json"))["user_id"])')
export ORG_IDS_JSON=$(python -c 'import json;print(json.dumps(json.load(open("perf_multi.json"))["org_ids"]))')
export FROM_DATE=$(python -c 'import json;print(json.load(open("perf_multi.json"))["month_start"])')
export TO_DATE=$(python -c 'import json;print(json.load(open("perf_multi.json"))["today"])')
```
3. Seed 10k transactions per org:
```bash
python -c "import json; d=json.load(open('perf_multi.json')); json.dump(d['org_ids'], open('perf_org_ids.json','w'))"
python scripts/seed_load_dataset.py --org-ids-file perf_org_ids.json --created-by "$USER_ID" --months 12 --rows 10000
```
4. Run profiles:
```bash
k6 run scripts/loadtest/k6-many-org-dashboard.js -e BASE_URL=http://localhost:8000/api/v1 -e ACCESS_TOKEN="$ACCESS_TOKEN" -e ORG_IDS_JSON="$ORG_IDS_JSON" -e FROM_DATE="$FROM_DATE" -e TO_DATE="$TO_DATE"
k6 run scripts/loadtest/k6-report-burst.js -e BASE_URL=http://localhost:8000/api/v1 -e ACCESS_TOKEN="$ACCESS_TOKEN" -e ORG_IDS_JSON="$ORG_IDS_JSON" -e WEEK_START=2026-03-09
k6 run scripts/loadtest/k6-mixed-churn.js -e BASE_URL=http://localhost:8000/api/v1 -e ACCESS_TOKEN="$ACCESS_TOKEN" -e ORG_IDS_JSON="$ORG_IDS_JSON" -e FROM_DATE="$FROM_DATE" -e TO_DATE="$TO_DATE"
k6 run scripts/loadtest/k6-read-hotpaths.js -e BASE_URL=http://localhost:8000/api/v1 -e ACCESS_TOKEN="$ACCESS_TOKEN" -e ORG_IDS_JSON="$ORG_IDS_JSON" -e FROM_DATE="$FROM_DATE" -e TO_DATE="$TO_DATE" -e RATE=13 -e RUNTIME_METRICS_ENABLED=false
k6 run scripts/loadtest/k6-runtime-observability.js -e BASE_URL=http://localhost:8000/api/v1 -e ACCESS_TOKEN="$ACCESS_TOKEN" -e ORG_IDS_JSON="$ORG_IDS_JSON" -e RATE=2
k6 run scripts/loadtest/k6-write-heavy.js -e BASE_URL=http://localhost:8000/api/v1 -e ACCESS_TOKEN="$ACCESS_TOKEN" -e ORG_IDS_JSON="$ORG_IDS_JSON" -e WEEK_START=2026-03-09
```

## Performance expectations and limits
- Single-org read path target (100k tx):
  - summary/cashflow/transactions p95 under 2.2s.
- Read guardrail under this stack/config:
  - user-facing read profile at `RATE=13` with `RUNTIME_METRICS_ENABLED=false`.
- Many-org dashboard target (100 orgs):
  - summary/cashflow p95 under 2.2s.
  - runway/alerts p95 under 1.8s.
- Report burst enqueue target:
  - `/reports/generate` p95 under 2.0s and request failures < 3%.
- Mixed churn target:
  - failures < 4% with API responsiveness maintained for core reads.

Limits (current phase):
- These profiles validate API/service behavior and queue pressure, not full worker throughput SLOs.
- MinIO/network variability can materially affect report completion timing outside API enqueue latency.

## Operational hardening notes
- Usage metering creation is race-hardened to avoid duplicate-key failures under concurrent report enqueue (`uq_usage_org_metric_period`).
- Celery worker registration is explicit for alerts/forecasts/outbox task modules to prevent unregistered-task drops under churn.
- SQLAlchemy async pool is explicitly bounded via env (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT_SECONDS`, `DB_POOL_RECYCLE_SECONDS`) to reduce connection spikes under mixed churn.
- Worker concurrency/prefetch are bounded (`WORKER_CONCURRENCY`, `WORKER_PREFETCH_MULTIPLIER`) to avoid exhausting Postgres `max_connections` during enqueue/recompute bursts.
- API and worker can now use separate pool envelopes via role-aware settings (`APP_ROLE` + `API_DB_*` / `WORKER_DB_*`) so API read/write latency can be tuned independently from Celery throughput.
- `/reports/generate` uses a read-only idempotent fast path for already-generated `(org_id, week_start)` reports, avoiding extra `job_state`/audit writes during churn.

## CI workflow
Workflow: `.github/workflows/perf.yml`

What it does:
1. boots docker stack
2. bootstraps test org/user/token
3. seeds 5k-row CI dataset
4. runs k6 smoke profile
5. runs split perf gates:
   - `k6-read-hotpaths` pass 1 (`RATE=13`, `RUNTIME_METRICS_ENABLED=false`)
   - `k6-read-hotpaths` pass 2 (`RATE=13`, `RUNTIME_METRICS_ENABLED=false`)
   - `k6-runtime-observability` (`RATE=2`)
6. evaluates guardrails from `slo_guardrails.json` via `evaluate_perf_gates.py`
7. uploads artifacts (`perf-artifacts/*`) containing:
   - per-run k6 summary exports
   - consolidated gate report (`perf_gate_summary.json`, `perf_gate_summary.md`)

For deeper tests, run local scalability profiles above with larger seeds (100k single org, 100x10k many-org).
