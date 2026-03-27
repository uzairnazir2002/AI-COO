# ADR 0012: Realtime Updates via SSE with Polling Fallback

## Status
Accepted

## Context
Dashboard/reporting UX benefits from near-realtime updates, but some environments/proxies may not reliably support long-lived SSE streams.

## Decision
- Provide server-sent events endpoint:
  - `GET /api/v1/events/stream?org_id=...`
- Stream org-scoped summary and open-alert counts at configurable interval.
- Keep polling as first-class fallback behavior in clients/docs (poll every 15-30 seconds when SSE is unavailable).

## Consequences
- Improves perceived freshness without introducing websocket infrastructure.
- Preserves compatibility in restricted environments via polling fallback.
- Requires org membership checks on stream open to maintain tenant isolation.
