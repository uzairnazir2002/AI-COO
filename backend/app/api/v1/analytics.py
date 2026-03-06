import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.transaction import Transaction
from app.domain.models.user import User
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.schemas.analytics import CashPoint, CashflowOut, SummaryOut
from app.jobs.tasks.alerts import recalc_alerts
from app.jobs.tasks.forecasts import recalc_forecasts
from app.domain.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/summary", response_model=SummaryOut)
async def summary(
    org_id: uuid.UUID = Query(...),
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    out = await AnalyticsService(AnalyticsRepo(db)).summary(org_id, from_date, to_date)
    return SummaryOut(**out)


@router.get("/cashflow", response_model=CashflowOut)
async def cashflow(
    org_id: uuid.UUID = Query(...),
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    granularity: str = "month",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    trunc = "day" if granularity == "day" else "week" if granularity == "week" else "month"
    q = await db.execute(
        select(
            func.date_trunc(trunc, Transaction.date).label("d"),
            func.sum(case((Transaction.type == "REVENUE", Transaction.amount), else_=0)).label("rev"),
            func.sum(case((Transaction.type == "EXPENSE", Transaction.amount), else_=0)).label("exp"),
        )
        .where(Transaction.org_id == org_id, Transaction.date >= from_date, Transaction.date <= to_date)
        .group_by("d")
        .order_by("d")
    )
    points = []
    for d, rev, exp in q.all():
        points.append(CashPoint(date=d.date(), revenue=rev or 0, expense=exp or 0, net=(rev or 0) - (exp or 0)))
    return CashflowOut(points=points)


@router.post("/recompute")
async def recompute(
    request: Request,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    if ctx.role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")
    correlation_id = getattr(getattr(user, "id", None), "hex", None)
    headers = {"x-request-id": getattr(request.state, "request_id", "")}
    alerts_job = recalc_alerts.apply_async(args=[str(org_id), correlation_id], headers=headers)
    forecast_job = recalc_forecasts.apply_async(args=[str(org_id), correlation_id], headers=headers)
    return {"ok": True, "alerts_job_id": alerts_job.id, "forecast_job_id": forecast_job.id}
