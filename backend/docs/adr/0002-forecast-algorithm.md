# ADR 0002: Forecast model

## Decision
Use a deterministic baseline model from trailing monthly averages with scenario multipliers.

## Why
- Transparent and explainable for SMB MVP.
- Stable fallback without external ML dependency.

## Details
- Base: avg revenue/expense from lookback.
- High: revenue +10%, expense -5%.
- Low: revenue -10%, expense +10%.
- Supports per-month user overrides.
