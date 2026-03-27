# CI Env-Gated Lanes

The following CI jobs are intentionally gated by repository variables and/or secrets.

## Variables

- `CI_E2E_COOKIE_LANE=1` enables `playwright-cookie-csrf`
- `CI_E2E_SSE_LANE=1` enables `playwright-sse-fallback`
- `CI_E2E_VISUAL_LANE=1` enables `playwright-visual`
- `CI_E2E_PLAID_LANE=1` enables `plaid-epic-a` (requires Plaid secrets)
- `CI_AI_LIVE_MODE_LANE=1` enables `ai-live-mode` (requires OpenAI secret)
- `AI_OPENAI_MODEL` optional override for AI live lane model (default `gpt-4o-mini`)

## Required secrets by lane

### Plaid lane

- `PLAID_CLIENT_ID`
- `PLAID_SECRET`
- `PLAID_WEBHOOK_SECRET` (recommended)

### AI live lane

- `AI_OPENAI_API_KEY`

## Manual workflow_dispatch switches

- `run_cookie_lane=true`
- `run_sse_lane=true`
- `run_visual_lane=true`
- `run_plaid_lane=true`
- `run_ai_live_lane=true`

Use these when variables are not permanently enabled.

## Release usage

- Treat these env-gated lanes as mandatory checks when executing the production checklist:
  - `docs/operations/release_checklist.md`
