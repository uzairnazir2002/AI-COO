import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.repos.forecast_repo import ForecastRepo
from app.domain.schemas.forecast import ForecastOut, ForecastOverrideIn, ForecastPoint
from app.domain.services.forecast_service import ForecastService

router = APIRouter()


@router.get("", response_model=ForecastOut)
async def get_forecast(
    org_id: uuid.UUID = Query(...),
    months: int = 3,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    svc = ForecastService(ForecastRepo(db), AnalyticsRepo(db))
    rows = await svc.ensure_forecasts(org_id, months)
    await db.commit()
    scenarios = {"base": [], "high": [], "low": []}
    for r in rows:
        p = ForecastPoint(
            month=r.month,
            revenue_pred=r.revenue_pred,
            expense_pred=r.expense_pred,
            confidence_low=r.confidence_low,
            confidence_high=r.confidence_high,
        )
        scenarios[str(r.scenario).lower()].append(p)
    return ForecastOut(scenarios=scenarios, generated_at=datetime.utcnow())


@router.post("/override")
async def override_forecast(
    body: ForecastOverrideIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    if ctx.role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")
    svc = ForecastService(ForecastRepo(db), AnalyticsRepo(db))
    ok = await svc.override(body.org_id, body.month, body.scenario, body.revenue_override, body.expense_override)
    await db.commit()
    return {"ok": ok}
