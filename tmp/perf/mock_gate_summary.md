# Perf Gate Summary

## Guardrails
- Read `RATE`: 13
- Runtime observability `RATE`: 2

## Read Hotpaths

| Pass | Summary p95 (ms) | Cashflow p95 (ms) | Transactions p95 (ms) | Alerts p95 (ms) | Failure rate | Dropped iterations | Breach |
|---|---:|---:|---:|---:|---:|---:|---:|
| read_pass_1 | 1000.00 | 1100.00 | 900.00 | 800.00 | 0.0000 | 1 | False |
| read_pass_2 | 1000.00 | 1100.00 | 900.00 | 800.00 | 0.0000 | 1 | False |

## Runtime Observability

| Runtime metrics p95 (ms) | Failure rate | Dropped iterations | Breach |
|---:|---:|---:|---:|
| 700.00 | 0.0000 | 1 | False |

## Gate Result
- `PASS`
