# Secret Hygiene Checklist

Use this checklist before every staging/production release.

## 1) Repository hygiene

- Confirm `.env` and `.env.production` are ignored and not committed.
- Run:
  - `python scripts/ops/secret_hygiene_audit.py --root . --env-file .env.example`
- Ensure report status is `PASS` and no critical findings exist.

## 2) Secret injection policy

- Provide runtime secrets only through CI/CD secret store or deployment secret manager.
- Never place live keys in:
  - `.env.example`
  - source code
  - test fixtures
  - logs

## 3) Required production secrets

- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `MINIO_SECRET_KEY`
- `SMTP_PASSWORD`
- `AI_OPENAI_API_KEY` (if `AI_PROVIDER=openai`)
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `PLAID_SECRET`
- `PLAID_WEBHOOK_SECRET`

## 4) Rotation cadence

- Rotate app/platform keys on a fixed schedule (e.g., every 90 days).
- Rotate immediately for any accidental disclosure.
- Record rotation event in operations log:
  - key name
  - rotated at (UTC)
  - owner
  - impacted services

## 5) Incident response for key exposure

1. Revoke/rotate affected key.
2. Redeploy services with new secret value.
3. Verify health and critical flows (`/health`, auth/login, reports, integrations, AI summary).
4. Review audit logs for suspicious access windows.
5. Document postmortem and prevention action.

## 6) Release gate

- Do not tag or release if secret hygiene audit fails.
