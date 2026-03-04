from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.schemas.ai import AISummaryOut, AISummaryRequest
from app.domain.services.ai_service import AIService
from app.domain.services.analytics_service import AnalyticsService

router = APIRouter()


@router.post("/summary", response_model=AISummaryOut)
async def ai_summary(body: AISummaryRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_org_context(org_id=body.org_id, user=user, db=db)
    summary = await AnalyticsService(AnalyticsRepo(db)).summary(body.org_id, body.from_date, body.to_date)
    alerts = await AlertRepo(db).list_alerts(body.org_id, "OPEN")
    metrics = {"kpis": summary, "alerts": [{"title": a.title, "severity": a.severity} for a in alerts]}
    return await AIService().summary(metrics)
