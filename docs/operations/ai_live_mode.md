# AI Live Mode Verification

Use this checklist before enabling live OpenAI mode in non-local environments.

## 1) Set env values

```env
AI_PROVIDER=openai
AI_OPENAI_API_KEY=<your-api-key>
AI_OPENAI_MODEL=gpt-4o-mini
AI_OPENAI_BASE_URL=https://api.openai.com/v1
AI_TIMEOUT_SECONDS=20
```

Restart backend after env changes.

## 2) Verify provider health

```bash
curl "http://localhost:8000/api/v1/ai/health?org_id=<ORG_ID>&live_check=true" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Expected:
- `provider.provider = "openai"`
- `provider.configured = true`
- `provider.healthy = true`
- `provider.live_check_performed = true`
- `fallback_ready = true`

Automated verification:

```bash
python scripts/ops/verify_ai_live_mode.py \
  --api-base-url http://localhost:8000/api/v1 \
  --database-url postgresql://ai_coo:ai_coo@localhost:5432/ai_coo \
  --live-check \
  --verify-fallback-test \
  --fallback-test-path backend/app/tests/test_ai_service.py::test_ai_service_falls_back_on_provider_error
```

## 3) Verify grounded summary + fallback behavior

Run backend AI tests:

```bash
cd backend
..\.venv\Scripts\python.exe -m pytest app/tests/test_ai_service.py app/tests/test_ai_chat_endpoint.py -q
```

This validates:
- grounded outputs pass
- invalid/hallucinated outputs trigger deterministic fallback
- AI health endpoint reports provider/fallback readiness
