# ADR 0003: Cash balance definition

## Decision
Use `OrganizationSetting.starting_cash` + net transaction flow.

## Why
- Keeps runway, dashboard, and report math consistent.
- Gives operators explicit control over opening balance.

## Formula
`cash = starting_cash + total_revenue - total_expense`
