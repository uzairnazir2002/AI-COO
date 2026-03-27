# Epic F Delta (AI Chat Assistant)

## Scope Delivered
- Added persistent AI chat domain model:
  - `ai_chat_sessions`
  - `ai_chat_messages`
- Added backend API endpoints:
  - `POST /api/v1/ai/chat/sessions`
  - `GET /api/v1/ai/chat/sessions?org_id=...`
  - `GET /api/v1/ai/chat/sessions/{session_id}?org_id=...`
  - `POST /api/v1/ai/chat`
- Reused semantic grounding validator path:
  - chat generation now uses the same `AISemanticGroundingValidator` enforcement used by AI summary.
  - fallback response path is applied when grounding validation fails.
- Added org-scoped audit records for:
  - chat session creation
  - assistant response creation
- Added frontend AI Chat workspace:
  - `/app/assistant` page with session list, chat composer, and threaded messages
  - grounded/fallback indicator badge on assistant messages

## Evidence
- Migration:
  - `backend/migrations/versions/0028_ai_chat_assistant_foundation.py`
- Models:
  - `backend/app/domain/models/ai_chat_session.py`
  - `backend/app/domain/models/ai_chat_message.py`
- Repo/service:
  - `backend/app/domain/repos/ai_chat_repo.py`
  - `backend/app/domain/services/ai_chat_service.py`
  - `backend/app/domain/services/ai_service.py`
- API/schema:
  - `backend/app/api/v1/ai.py`
  - `backend/app/domain/schemas/ai.py`
- Frontend:
  - `frontend/src/app/app/assistant/page.tsx`
  - `frontend/src/features/ai-chat/hooks.ts`
  - `frontend/src/lib/api/endpoints.ts`
  - `frontend/src/lib/api/schemas.ts`
  - `frontend/src/lib/query/keys.ts`
  - `frontend/src/components/shell/app-shell.tsx`
  - `frontend/src/components/shell/command-palette.tsx`
  - `frontend/src/components/shell/breadcrumbs.tsx`
  - `frontend/e2e/ai-chat.spec.ts`

## Verification
- Command:
  - `.venv\\Scripts\\python.exe -m pytest backend/app/tests/test_ai_chat_endpoint.py backend/app/tests/test_ai_chat_service.py`
- Result:
  - `8 passed`
- Command:
  - `.venv\\Scripts\\python.exe -m ruff check backend/app/api/v1/ai.py backend/app/domain/services/ai_chat_service.py backend/app/tests/test_ai_chat_endpoint.py backend/app/tests/test_ai_chat_service.py`
- Result:
  - `All checks passed`
- Command:
  - `npm run lint && npm run build` (frontend)
- Result:
  - lint clean and build successful with `/app/assistant` route emitted.
- Command:
  - `npx playwright test e2e/ai-chat.spec.ts` (targeted local stack: frontend `:3002`, backend `:8001`)
- Result:
  - `1 passed` (`AI chat flow: create session -> send message -> grounded/fallback indicator visible`).

## Remaining For Full Epic F Closure
- Optional read-cache strategy for recent chat session loads under high concurrency.
