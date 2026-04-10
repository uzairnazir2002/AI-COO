import uuid
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.api.period_month import parse_period_month_query
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.budget_repo import BudgetRepo
from app.domain.repos.job_repo import JobRepo
from app.domain.repos.notification_repo import NotificationRepo
from app.domain.schemas.budget import BudgetCreateIn, BudgetOut, BudgetUpdateIn
from app.domain.services.alerts_refresh_service import AlertRefreshService
from app.domain.services.budget_service import BudgetService
from app.domain.services.notification_service import NotificationService

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


def _apply_alert_recalc_headers(response: Response, *, task_id: str, status: str, enqueued: bool) -> None:
    response.headers["X-Alert-Recalc-Task-Id"] = task_id
    response.headers["X-Alert-Recalc-Status"] = status
    response.headers["X-Alert-Recalc-Queued"] = "true" if enqueued else "false"


async def _notify_alert_recalc(
    *,
    db: AsyncSession,
    org_id: uuid.UUID,
    source: str,
    task_id: str,
    status: str,
    enqueued: bool,
) -> None:
    title = "Alert refresh queued" if enqueued else "Alert refresh already pending"
    message = (
        f"{source} enqueued alert refresh job {task_id} ({status})."
        if enqueued
        else f"{source} reused pending alert refresh job {task_id} ({status})."
    )
    await NotificationService(NotificationRepo(db)).create_org_notification(
        org_id=org_id,
        category="OPS",
        title=title,
        message=message,
        link="/app/activity",
        metadata_json={
            "event": "alert.recalc.enqueue",
            "source": source,
            "task_id": task_id,
            "status": status,
            "enqueued": enqueued,
        },
    )


@router.get("", response_model=list[BudgetOut])
async def list_budgets(
    org_id: uuid.UUID = Query(...),
    period: str | None = Query(
        default=None,
        description="Month as YYYY-MM or first day YYYY-MM-DD (normalized to month start).",
    ),
    budget_type: str | None = Query(default=None),
    include_history: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    period_month = parse_period_month_query(period)
    svc = BudgetService(BudgetRepo(db))
    try:
        rows = await svc.list_budgets(
            org_id=org_id,
            period_month=period_month,
            budget_type=budget_type,
            include_history=include_history,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [BudgetOut.model_validate(row) for row in rows]


@router.post("", response_model=BudgetOut)
async def create_budget(
    request: Request,
    response: Response,
    body: BudgetCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = BudgetService(BudgetRepo(db))
    try:
        budget = await svc.create_budget(
            org_id=body.org_id,
            actor_user_id=user.id,
            category=body.category,
            period_month=body.period_month,
            planned_amount=body.planned_amount,
            budget_type=body.budget_type,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "budget.create",
        "budget",
        str(budget.id),
        {
            "category": budget.category,
            "period_month": str(budget.period_month),
            "budget_type": budget.budget_type,
            "version": budget.version,
        },
    )
    refresh = await AlertRefreshService(JobRepo(db)).enqueue_recalc(
        org_id=body.org_id,
        correlation_id=str(user.id),
        request_id=getattr(request.state, "request_id", None),
        reason="budget.create",
    )
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "alert.recalc.enqueue",
        "job_state",
        refresh.task_id,
        {"source": "budget.create", "status": refresh.status, "enqueued": refresh.enqueued},
    )
    await _notify_alert_recalc(
        db=db,
        org_id=body.org_id,
        source="budget.create",
        task_id=refresh.task_id,
        status=refresh.status,
        enqueued=refresh.enqueued,
    )
    _apply_alert_recalc_headers(
        response,
        task_id=refresh.task_id,
        status=refresh.status,
        enqueued=refresh.enqueued,
    )
    await db.commit()
    return BudgetOut.model_validate(budget)


@router.put("/{budget_id}", response_model=BudgetOut)
async def update_budget(
    request: Request,
    response: Response,
    budget_id: uuid.UUID,
    body: BudgetUpdateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = BudgetService(BudgetRepo(db))
    try:
        budget = await svc.update_budget_version(
            org_id=body.org_id,
            actor_user_id=user.id,
            budget_id=budget_id,
            planned_amount=body.planned_amount,
            notes=body.notes,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Budget not found":
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=422, detail=message) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "budget.update",
        "budget",
        str(budget.id),
        {
            "source_budget_id": str(budget_id),
            "category": budget.category,
            "period_month": str(budget.period_month),
            "budget_type": budget.budget_type,
            "version": budget.version,
        },
    )
    refresh = await AlertRefreshService(JobRepo(db)).enqueue_recalc(
        org_id=body.org_id,
        correlation_id=str(user.id),
        request_id=getattr(request.state, "request_id", None),
        reason="budget.update",
    )
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "alert.recalc.enqueue",
        "job_state",
        refresh.task_id,
        {"source": "budget.update", "status": refresh.status, "enqueued": refresh.enqueued},
    )
    await _notify_alert_recalc(
        db=db,
        org_id=body.org_id,
        source="budget.update",
        task_id=refresh.task_id,
        status=refresh.status,
        enqueued=refresh.enqueued,
    )
    _apply_alert_recalc_headers(
        response,
        task_id=refresh.task_id,
        status=refresh.status,
        enqueued=refresh.enqueued,
    )
    await db.commit()
    return BudgetOut.model_validate(budget)
