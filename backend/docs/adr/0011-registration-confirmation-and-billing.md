# ADR 0011: Registration Confirmation + Owner Billing Placeholder

## Status
Accepted

## Context
MVP needed:
- explicit account confirmation workflow after registration
- owner-only billing placeholder management for org administration

## Decision
- Add `account_confirmation_tokens` to store hashed one-time confirmation tokens with expiry/used timestamps.
- Registration creates inactive users (`is_active=false`) and emits outbox `email.send` with confirmation token instructions.
- `POST /api/v1/auth/confirm` activates the account when token is valid.
- Add `organization_billing` table and owner-only endpoints:
  - `GET /api/v1/organizations/{org_id}/billing`
  - `PUT /api/v1/organizations/{org_id}/billing`

## Consequences
- Prevents immediate login before confirmation (harder for account abuse).
- Keeps billing scope as placeholder metadata without introducing payment processing.
- Preserves tenant/RBAC boundaries by org and owner role.
