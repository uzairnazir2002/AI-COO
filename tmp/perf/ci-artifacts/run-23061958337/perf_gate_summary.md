# Perf Gate Summary

## Guardrails
- Read `RATE`: 13
- Runtime observability `RATE`: 2

## Read Hotpaths

| Pass | Summary p95 (ms) | Cashflow p95 (ms) | Transactions p95 (ms) | Alerts p95 (ms) | Failure rate | Dropped iterations | Breach |
|---|---:|---:|---:|---:|---:|---:|---:|
| read_pass_1 | 8.55 | 4.22 | 6.26 | 3.63 | 0.0000 | 0 | False |
| read_pass_2 | 8.25 | 4.19 | 6.20 | 3.55 | 0.0000 | 0 | False |

## Runtime Observability

| Runtime metrics p95 (ms) | Failure rate | Dropped iterations | Breach |
|---:|---:|---:|---:|
| 1.41 | 0.0000 | 0 | False |

## Gate Result
- `PASS`
