import uuid
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.api.period_month import parse_period_month_query
from app.db.session import get_db
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.budget_repo import BudgetRepo
from app.domain.repos.idempotency_repo import IdempotencyRepo
from app.domain.repos.location_repo import LocationRepo
from app.domain.models.transaction import Transaction
from app.domain.models.user import User
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.repos.job_repo import JobRepo
from app.domain.schemas.budget import BudgetVarianceLineOut, BudgetVarianceOut, BudgetVarianceTotalsOut
from app.domain.schemas.analytics import (
    AnalyticsRecomputeOut,
    CashPoint,
    CashflowOut,
    LocationBenchmarkItemOut,
    LocationBenchmarkOut,
    LocationBenchmarkTotalsOut,
    SummaryOut,
)
from app.domain.services.read_cache_service import analytics_summary_cache_key, cache_get_json, cache_set_json
from app.jobs.tasks.analytics import recompute_org_analytics
from app.domain.services.analytics_service import AnalyticsService
from app.domain.services.budget_service import BudgetService
from app.domain.services.errors import NotFoundError
from app.domain.services.idempotency_service import IdempotencyService
from app.domain.services.location_service import LocationService
from app.core.config import get_settings
from app.utils.idempotency_request import request_hash

router = APIRouter()


@router.get("/summary", response_model=SummaryOut)
async def summary(
    org_id: uuid.UUID = Query(...),
    location_id: uuid.UUID | None = Query(default=None),
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
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
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    settings = get_settings()
    cache_key = analytics_summary_cache_key(org_id, from_date, to_date, location_id)
    cached = await cache_get_json(cache_key)
    if isinstance(cached, dict):
        return SummaryOut.model_validate(cached)
    out = await AnalyticsService(AnalyticsRepo(db)).summary(org_id, from_date, to_date, location_id=location_id)
    result = SummaryOut(**out)
    await cache_set_json(cache_key, result.model_dump(mode="json"), settings.analytics_summary_cache_ttl_seconds)
    return result


@router.get("/cashflow", response_model=CashflowOut)
async def cashflow(
    org_id: uuid.UUID = Query(...),
    location_id: uuid.UUID | None = Query(default=None),
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    granularity: str = "month",
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
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    trunc = "day" if granularity == "day" else "week" if granularity == "week" else "month"
    filters = [Transaction.org_id == org_id, Transaction.date >= from_date, Transaction.date <= to_date]
    if location_id is not None:
        filters.append(Transaction.location_id == location_id)
    q = await db.execute(
        select(
            func.date_trunc(trunc, Transaction.date).label("d"),
            func.sum(case((Transaction.type == "REVENUE", Transaction.amount), else_=0)).label("rev"),
            func.sum(case((Transaction.type == "EXPENSE", Transaction.amount), else_=0)).label("exp"),
        )
        .where(*filters)
        .group_by("d")
        .order_by("d")
    )
    points = []
    for d, rev, exp in q.all():
        points.append(CashPoint(date=d.date(), revenue=rev or 0, expense=exp or 0, net=(rev or 0) - (exp or 0)))
    return CashflowOut(points=points)


@router.get("/budget-variance", response_model=BudgetVarianceOut)
async def budget_variance(
    org_id: uuid.UUID = Query(...),
    location_id: uuid.UUID | None = Query(default=None),
    period: str | None = Query(
        default=None,
        description="Month as YYYY-MM or YYYY-MM-DD (normalized to month start). Defaults to current month.",
    ),
    budget_type: str | None = Query(default=None),
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
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    period_month = parse_period_month_query(period) or date.today().replace(day=1)
    svc = BudgetService(BudgetRepo(db))
    try:
        out = await svc.budget_variance(
            org_id=org_id,
            period_month=period_month,
            budget_type=budget_type,
            location_id=location_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return BudgetVarianceOut(
        org_id=out["org_id"],
        period_month=out["period_month"],
        budget_type=out["budget_type"],
        totals=BudgetVarianceTotalsOut(**out["totals"]),
        lines=[
            BudgetVarianceLineOut(
                category=line.category,
                budget_type=line.budget_type,
                planned_amount=line.planned_amount,
                actual_amount=line.actual_amount,
                variance_amount=line.variance_amount,
                variance_pct=line.variance_pct,
            )
            for line in out["lines"]
        ],
    )


@router.get("/location-benchmark", response_model=LocationBenchmarkOut)
async def location_benchmark(
    org_id: uuid.UUID = Query(...),
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="'from' must be before or equal to 'to'")
    out = await AnalyticsService(AnalyticsRepo(db)).location_benchmark(
        org_id=org_id,
        from_date=from_date,
        to_date=to_date,
    )
    return LocationBenchmarkOut(
        org_id=out["org_id"],
        from_date=out["from_date"],
        to_date=out["to_date"],
        totals=LocationBenchmarkTotalsOut(**out["totals"]),
        locations=[LocationBenchmarkItemOut(**row) for row in out["locations"]],
    )


@router.post("/recompute", response_model=AnalyticsRecomputeOut)
async def recompute(
    request: Request,
    org_id: uuid.UUID = Query(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    if ctx.role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")
    idem_service = IdempotencyService(IdempotencyRepo(db))
    idem_hash = request_hash({"org_id": org_id})
    replay = await idem_service.get_replay(
        org_id=org_id,
        user_id=user.id,
        endpoint="POST /api/v1/analytics/recompute",
        idempotency_key=idempotency_key,
        request_hash=idem_hash,
    )
    if replay:
        return JSONResponse(status_code=replay.status_code, content=replay.response_json)
    correlation_id = str(getattr(user, "id", ""))
    dedupe_key = f"analytics-recompute:{org_id}"
    job_repo = JobRepo(db)
    existing_job = await job_repo.by_dedupe_key(dedupe_key, org_id)
    if existing_job and existing_job.status in {"PENDING", "RUNNING", "RETRYING"}:
        response_body = AnalyticsRecomputeOut(
            ok=True,
            job_id=existing_job.task_id,
            status=existing_job.status,
            result=existing_job.result,
        ).model_dump(mode="json")
        await idem_service.store_response(
            org_id=org_id,
            user_id=user.id,
            endpoint="POST /api/v1/analytics/recompute",
            idempotency_key=idempotency_key,
            request_hash=idem_hash,
            status_code=200,
            response_json=response_body,
        )
        await db.commit()
        return response_body

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
    response_body = AnalyticsRecomputeOut(ok=True, job_id=task_id, status="PENDING", result=None).model_dump(mode="json")
    await idem_service.store_response(
        org_id=org_id,
        user_id=user.id,
        endpoint="POST /api/v1/analytics/recompute",
        idempotency_key=idempotency_key,
        request_hash=idem_hash,
        status_code=200,
        response_json=response_body,
    )
    await db.commit()
    return response_body
