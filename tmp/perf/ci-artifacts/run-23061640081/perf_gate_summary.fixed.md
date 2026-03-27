# Perf Gate Summary

## Guardrails
- Read `RATE`: 13
- Runtime observability `RATE`: 2

## Read Hotpaths

| Pass | Summary p95 (ms) | Cashflow p95 (ms) | Transactions p95 (ms) | Alerts p95 (ms) | Failure rate | Dropped iterations | Breach |
|---|---:|---:|---:|---:|---:|---:|---:|
| read_pass_1 | 8.36 | 4.42 | 6.54 | 3.73 | 0.0000 | 0 | False |
| read_pass_2 | 8.40 | 4.42 | 6.52 | 3.68 | 0.0000 | 0 | False |

## Runtime Observability

| Runtime metrics p95 (ms) | Failure rate | Dropped iterations | Breach |
|---:|---:|---:|---:|
| 1.45 | 0.0000 | 0 | False |

## Gate Result
- `PASS`
