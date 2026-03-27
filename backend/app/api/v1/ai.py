import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.ai_chat_repo import AIChatRepo
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.plan_repo import PlanRepo
from app.domain.schemas.ai import (
    AIChatMessageOut,
    AIChatOut,
    AIChatRequest,
    AIChatSessionCreateIn,
    AIChatSessionDetailOut,
    AIChatSessionOut,
    AIHealthOut,
    AIProviderHealthOut,
    AISummaryOut,
    AISummaryRequest,
)
from app.domain.services.ai_chat_service import AIChatService
from app.domain.services.ai_service import AIService
from app.domain.services.analytics_service import AnalyticsService
from app.domain.services.errors import NotFoundError
from app.domain.services.usage_service import METRIC_AI_SUMMARIES, UsageService
from app.infra.ai_client import generate_summary_stub, get_ai_provider_health

router = APIRouter()


@router.get("/health", response_model=AIHealthOut)
async def ai_health(
    org_id: uuid.UUID = Query(...),
    live_check: bool = Query(default=False),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    provider = AIProviderHealthOut.model_validate(get_ai_provider_health(live_check=live_check))

    fallback_ready = True
    try:
        generate_summary_stub({"kpis": {}, "alerts": []})
    except Exception:
        fallback_ready = False

    return AIHealthOut(provider=provider, fallback_ready=fallback_ready)


@router.post("/summary", response_model=AISummaryOut)
async def ai_summary(body: AISummaryRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_org_context(org_id=body.org_id, user=user, db=db)
    await UsageService(PlanRepo(db)).consume(body.org_id, METRIC_AI_SUMMARIES, delta=1)
    summary = await AnalyticsService(AnalyticsRepo(db)).summary(body.org_id, body.from_date, body.to_date)
    alerts = await AlertRepo(db).list_alerts(body.org_id, "OPEN")
    metrics = {"kpis": summary, "alerts": [{"title": a.title, "severity": a.severity} for a in alerts]}
    return await AIService().summary(metrics)


@router.post("/chat/sessions", response_model=AIChatSessionOut)
async def create_ai_chat_session(
    body: AIChatSessionCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=body.org_id, user=user, db=db)
    session = await AIChatService(
        AIChatRepo(db),
        AnalyticsRepo(db),
        AlertRepo(db),
    ).create_session(
        org_id=body.org_id,
        actor_user_id=user.id,
        title=body.title,
    )
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "ai.chat.session.create",
        "ai_chat_session",
        str(session.id),
        {"title": session.title},
    )
    await db.commit()
    return AIChatSessionOut.model_validate(session, from_attributes=True)


@router.get("/chat/sessions", response_model=list[AIChatSessionOut])
async def list_ai_chat_sessions(
    org_id: uuid.UUID = Query(...),
    mine_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    sessions = await AIChatService(
        AIChatRepo(db),
        AnalyticsRepo(db),
        AlertRepo(db),
    ).list_sessions(
        org_id=org_id,
        created_by_user_id=user.id if mine_only else None,
        limit=limit,
    )
    return [AIChatSessionOut.model_validate(session, from_attributes=True) for session in sessions]


@router.get("/chat/sessions/{session_id}", response_model=AIChatSessionDetailOut)
async def get_ai_chat_session(
    session_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    svc = AIChatService(AIChatRepo(db), AnalyticsRepo(db), AlertRepo(db))
    try:
        session, messages = await svc.get_session_with_messages(org_id=org_id, session_id=session_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AIChatSessionDetailOut(
        session=AIChatSessionOut.model_validate(session, from_attributes=True),
        messages=[AIChatMessageOut.model_validate(message, from_attributes=True) for message in messages],
    )


@router.post("/chat", response_model=AIChatOut)
async def ai_chat(
    body: AIChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=body.org_id, user=user, db=db)
    await UsageService(PlanRepo(db)).consume(body.org_id, METRIC_AI_SUMMARIES, delta=1)
    svc = AIChatService(AIChatRepo(db), AnalyticsRepo(db), AlertRepo(db))
    try:
        message = await svc.chat(
            org_id=body.org_id,
            session_id=body.session_id,
            actor_user_id=user.id,
            message=body.message,
            from_date=body.from_date,
            to_date=body.to_date,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "ai.chat.message.create",
        "ai_chat_session",
        str(body.session_id),
        {
            "assistant_message_id": str(message.id),
            "fallback_used": message.fallback_used,
        },
    )
    await db.commit()
    return AIChatOut(
        session_id=body.session_id,
        message=AIChatMessageOut.model_validate(message, from_attributes=True),
    )
