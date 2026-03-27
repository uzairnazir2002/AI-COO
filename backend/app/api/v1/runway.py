import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.repos.location_repo import LocationRepo
from app.domain.schemas.analytics import RunwayOut
from app.domain.services.analytics_service import AnalyticsService
from app.domain.services.errors import NotFoundError
from app.domain.services.location_service import LocationService

router = APIRouter()


@router.get("/runway", response_model=RunwayOut)
async def runway(
    org_id: uuid.UUID = Query(...),
    location_id: uuid.UUID | None = Query(default=None),
    lookback_months: int = 6,
    conservative: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    try:
        await LocationService(LocationRepo(db)).ensure_org_location(
            org_id=org_id,
            location_id=location_id,
            require_active=False,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    out = await AnalyticsService(AnalyticsRepo(db)).runway(
        org_id,
        lookback_months,
        conservative,
        location_id=location_id,
    )
    return RunwayOut(**out)
