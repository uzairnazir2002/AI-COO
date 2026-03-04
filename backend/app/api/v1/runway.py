import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.schemas.analytics import RunwayOut
from app.domain.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/runway", response_model=RunwayOut)
async def runway(
    org_id: uuid.UUID = Query(...),
    lookback_months: int = 6,
    conservative: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    out = await AnalyticsService(AnalyticsRepo(db)).runway(org_id, lookback_months, conservative)
    return RunwayOut(**out)
