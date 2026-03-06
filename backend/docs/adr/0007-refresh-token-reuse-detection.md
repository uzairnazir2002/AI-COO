# ADR 0007: Refresh Token Reuse Detection

## Status
Accepted

## Context
Refresh token rotation was implemented, but reuse of an already rotated token was treated as a generic unauthorized case with no theft signal.

## Decision
- Track replacement linkage in `token_sessions.replaced_by_token_hash`.
- On refresh rotation:
  - old session is revoked and linked to the new refresh token hash.
- On refresh request with a revoked session that has `replaced_by_token_hash`:
  - treat as token reuse/theft signal.
  - revoke all active sessions for the user.
  - write audit event `auth.refresh.reuse_detected`.

## Consequences
- Pros:
  - session theft signals become actionable.
  - stronger account/session containment.
- Cons:
  - some legitimate stale clients will require re-login after suspected reuse.
