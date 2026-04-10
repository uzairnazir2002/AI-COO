# RBAC matrix (product surfaces)

This is a **developer reference** for intended permissions. The **source of truth** remains backend `require_roles` / org context checks; UI disable/hide states should mirror this table.

| Capability | OWNER | EDITOR | VIEWER |
|------------|:-----:|:------:|:------:|
| **Orgs** — create / switch org | Yes | Yes | Yes |
| **Members** — invite / change roles | Yes | No* | No |
| **Org settings** — business / team | Yes | Yes | Read |
| **Billing / plan / Stripe portal** | Yes | No | No |
| **Sensitive actions (reauth)** | As required by API | As required | Denied where owner-only |
| **Transactions** — CRUD, import, bulk | Yes | Yes | Read |
| **Budgets** — create / edit | Yes | Yes | Read |
| **Forecast** — overrides | Yes | Yes | Read |
| **Alerts** — view | Yes | Yes | Yes |
| **Alerts** — assign / ack / dismiss | Yes | Yes | No (UI disabled) |
| **Reports** — generate / schedule intent | Yes | Yes | No (UI disabled) |
| **Reports** — view / download | Yes | Yes | Yes |
| **Assistant** — chat | Yes | Yes | Yes |
| **Inventory** — items / PO / stock events | Yes | Yes | Read |
| **Settings → Integrations** — Plaid / Stripe connect | Yes | Yes | Read / limited |
| **Admin console** — jobs | Yes | Yes | Yes (read-oriented) |
| **Admin console** — outbox / runtime / dead-letter / security ops | Yes | No | No |

\*Invite is **owner-only** in the current settings hooks (`requireOwner` for invite).

### Auth transport notes

- **Bearer** (`AUTH_COOKIE_MODE=false`): mutations from scripts/tests use `Authorization` unless UI is in cookie mode.
- **Cookie** (`AUTH_COOKIE_MODE=true`): session cookies + CSRF for mutating requests; align `NEXT_PUBLIC_AUTH_MODE` and `E2E_AUTH_MODE` for Playwright (see `frontend/README.md` and `frontend/e2e/global-setup.ts`).

### Verification

- Backend: role checks on routers (preferred over UI-only hiding).
- Frontend: `canEdit` / `isOwner` helpers and panel props such as `editable`.
- E2E: `e2e/rbac-viewer-api.spec.ts`, `e2e/rbac-viewer-settings-api.spec.ts` (bearer token API negatives).
