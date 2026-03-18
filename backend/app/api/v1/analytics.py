import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.repos.audit_repo import AuditRepo
from app.domain.models.transaction import Transaction
from app.domain.models.user import User
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.repos.job_repo import JobRepo
from app.domain.schemas.analytics import AnalyticsRecomputeOut, CashPoint, CashflowOut, SummaryOut
from app.domain.services.read_cache_service import analytics_summary_cache_key, cache_get_json, cache_set_json
from app.jobs.tasks.analytics import recompute_org_analytics
from app.domain.services.analytics_service import AnalyticsService
from app.core.config import get_settings

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
    settings = get_settings()
    cache_key = analytics_summary_cache_key(org_id, from_date, to_date)
    cached = await cache_get_json(cache_key)
    if isinstance(cached, dict):
        return SummaryOut.model_validate(cached)
    out = await AnalyticsService(AnalyticsRepo(db)).summary(org_id, from_date, to_date)
    result = SummaryOut(**out)
    await cache_set_json(cache_key, result.model_dump(mode="json"), settings.analytics_summary_cache_ttl_seconds)
    return result


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


@router.post("/recompute", response_model=AnalyticsRecomputeOut)
async def recompute(
    request: Request,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    if ctx.role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")
    correlation_id = str(getattr(user, "id", ""))
    dedupe_key = f"analytics-recompute:{org_id}"
    job_repo = JobRepo(db)
    existing_job = await job_repo.by_dedupe_key(dedupe_key, org_id)
    if existing_job and existing_job.status in {"PENDING", "RUNNING", "RETRYING"}:
        await db.commit()
        return AnalyticsRecomputeOut(
            ok=True,
            job_id=existing_job.task_id,
            status=existing_job.status,
            result=existing_job.result,
        )

    headers = {"x-request-id": getattr(request.state, "request_id", "")}
    task = recompute_org_analytics.apply_async(args=[str(org_id), correlation_id], headers=headers)
    task_id = str(task.id)
    await job_repo.upsert_pending(
        task_id=task_id,
        task_name="recompute_org_analytics",
        dedupe_key=dedupe_key,
        payload={"org_id": str(org_id)},
        org_id=org_id,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=correlation_id,
    )
    await AuditRepo(db).log(
        user.id,
        org_id,
        "analytics.recompute.enqueue",
        "job_state",
        task_id,
        {"job_id": task_id},
    )
    await db.commit()
    return AnalyticsRecomputeOut(ok=True, job_id=task_id, status="PENDING", result=None)
