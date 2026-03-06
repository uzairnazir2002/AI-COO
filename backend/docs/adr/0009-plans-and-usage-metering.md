# ADR 0009: Lightweight Plans And Usage Metering

## Status
Accepted

## Context
Before monetization, the platform needed enforceable soft limits to protect reliability and prepare for plan-based upgrades.

## Decision
- Add `organization_plans` table (default `FREE` plan per org).
- Add `usage_meters` table keyed by `(org_id, metric, period_start)`.
- Enforce soft limits on:
  - transaction writes (create + CSV import commits)
  - report generation
  - ai summary calls
- Return friendly `429` with current usage context when limits are exceeded.
- Expose read-only plan usage endpoint for settings UI.

## Consequences
- Pros:
  - controlled resource usage and clearer upgrade path.
  - no hard billing integration required for MVP.
- Cons:
  - additional write path on mutating endpoints.
