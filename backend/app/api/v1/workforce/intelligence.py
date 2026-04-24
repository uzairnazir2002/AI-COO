import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.schemas.workforce_intelligence import WorkforceDashboardIntelOut, WorkforceReportsSummaryOut
from app.domain.services.workforce_intelligence_service import WorkforceIntelligenceService

router = APIRouter()


@router.get("/dashboard", response_model=WorkforceDashboardIntelOut)
async def workforce_dashboard_intel(
    org_id: uuid.UUID = Query(...),
    as_of: date | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    d = as_of or date.today()
    return await WorkforceIntelligenceService(db).dashboard_intelligence(org_id=org_id, as_of=d)


@router.get("/reports/summary", response_model=WorkforceReportsSummaryOut)
async def workforce_reports_summary(
    org_id: uuid.UUID = Query(...),
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    return await WorkforceIntelligenceService(db).reports_summary(
        org_id=org_id, from_date=from_date, to_date=to_date
    )

