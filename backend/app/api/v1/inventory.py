import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.inventory_repo import InventoryRepo
from app.domain.repos.job_repo import JobRepo
from app.domain.repos.location_repo import LocationRepo
from app.domain.repos.notification_repo import NotificationRepo
from app.domain.schemas.inventory import (
    InventoryForecastOut,
    InventoryItemCreateIn,
    InventoryItemOut,
    InventoryPurchaseOrderCreateIn,
    InventoryPurchaseOrderOut,
    InventoryStockEventCreateIn,
    InventoryStockEventOut,
)
from app.domain.services.alerts_refresh_service import AlertRefreshService
from app.domain.services.errors import NotFoundError
from app.domain.services.inventory_service import InventoryService
from app.domain.services.location_service import LocationService
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


@router.get("/items", response_model=list[InventoryItemOut])
async def list_items(
    org_id: uuid.UUID = Query(...),
    include_inactive: bool = Query(default=False),
    location_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    if location_id is not None:
        await LocationService(LocationRepo(db)).ensure_org_location(org_id=org_id, location_id=location_id)
    rows = await InventoryService(InventoryRepo(db)).list_items(
        org_id=org_id,
        include_inactive=include_inactive,
        location_id=location_id,
    )
    return [InventoryItemOut.model_validate(row, from_attributes=True) for row in rows]


@router.post("/items", response_model=InventoryItemOut)
async def create_item(
    request: Request,
    response: Response,
    body: InventoryItemCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    if body.location_id is not None:
        await LocationService(LocationRepo(db)).ensure_org_location(org_id=body.org_id, location_id=body.location_id)
    svc = InventoryService(InventoryRepo(db))
    try:
        row = await svc.create_item(
            org_id=body.org_id,
            actor_user_id=user.id,
            location_id=body.location_id,
            sku=body.sku,
            name=body.name,
            unit_cost=body.unit_cost,
            reorder_point=body.reorder_point,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "inventory.item.create",
        "inventory_item",
        str(row.id),
        {"sku": row.sku, "name": row.name, "location_id": str(row.location_id) if row.location_id else None},
    )
    refresh = await AlertRefreshService(JobRepo(db)).enqueue_recalc(
        org_id=body.org_id,
        correlation_id=str(user.id),
        request_id=getattr(request.state, "request_id", None),
        reason="inventory.item.create",
    )
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "alert.recalc.enqueue",
        "job_state",
        refresh.task_id,
        {"source": "inventory.item.create", "status": refresh.status, "enqueued": refresh.enqueued},
    )
    await _notify_alert_recalc(
        db=db,
        org_id=body.org_id,
        source="inventory.item.create",
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
    return InventoryItemOut.model_validate(row, from_attributes=True)


@router.post("/stock-events", response_model=InventoryStockEventOut)
async def create_stock_event(
    request: Request,
    response: Response,
    body: InventoryStockEventCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    if body.location_id is not None:
        await LocationService(LocationRepo(db)).ensure_org_location(org_id=body.org_id, location_id=body.location_id)
    svc = InventoryService(InventoryRepo(db))
    try:
        row, on_hand_qty = await svc.record_stock_event(
            org_id=body.org_id,
            actor_user_id=user.id,
            item_id=body.item_id,
            location_id=body.location_id,
            event_type=body.event_type,
            quantity=body.quantity,
            unit_cost=body.unit_cost,
            occurred_at=body.occurred_at,
            reference=body.reference,
            notes=body.notes,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "inventory.stock_event.create",
        "inventory_stock_event",
        str(row.id),
        {
            "item_id": str(body.item_id),
            "event_type": row.event_type,
            "quantity": str(row.quantity),
            "delta_qty": str(row.delta_qty),
            "on_hand_qty": str(on_hand_qty),
        },
    )
    refresh = await AlertRefreshService(JobRepo(db)).enqueue_recalc(
        org_id=body.org_id,
        correlation_id=str(user.id),
        request_id=getattr(request.state, "request_id", None),
        reason="inventory.stock_event.create",
    )
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "alert.recalc.enqueue",
        "job_state",
        refresh.task_id,
        {"source": "inventory.stock_event.create", "status": refresh.status, "enqueued": refresh.enqueued},
    )
    await _notify_alert_recalc(
        db=db,
        org_id=body.org_id,
        source="inventory.stock_event.create",
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
    return InventoryStockEventOut.model_validate(row, from_attributes=True)


@router.post("/purchase-orders", response_model=InventoryPurchaseOrderOut)
async def create_purchase_order(
    request: Request,
    response: Response,
    body: InventoryPurchaseOrderCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    if body.location_id is not None:
        await LocationService(LocationRepo(db)).ensure_org_location(org_id=body.org_id, location_id=body.location_id)
    svc = InventoryService(InventoryRepo(db))
    try:
        row = await svc.create_purchase_order(
            org_id=body.org_id,
            actor_user_id=user.id,
            item_id=body.item_id,
            location_id=body.location_id,
            quantity=body.quantity,
            unit_cost=body.unit_cost,
            expected_date=body.expected_date,
            external_ref=body.external_ref,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "inventory.purchase_order.create",
        "inventory_purchase_order",
        str(row.id),
        {
            "item_id": str(body.item_id),
            "quantity": str(row.quantity),
            "expected_date": str(row.expected_date),
            "location_id": str(row.location_id) if row.location_id else None,
        },
    )
    refresh = await AlertRefreshService(JobRepo(db)).enqueue_recalc(
        org_id=body.org_id,
        correlation_id=str(user.id),
        request_id=getattr(request.state, "request_id", None),
        reason="inventory.purchase_order.create",
    )
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "alert.recalc.enqueue",
        "job_state",
        refresh.task_id,
        {"source": "inventory.purchase_order.create", "status": refresh.status, "enqueued": refresh.enqueued},
    )
    await _notify_alert_recalc(
        db=db,
        org_id=body.org_id,
        source="inventory.purchase_order.create",
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
    return InventoryPurchaseOrderOut.model_validate(row, from_attributes=True)


@router.get("/forecast", response_model=InventoryForecastOut)
async def get_forecast(
    org_id: uuid.UUID = Query(...),
    lookback_days: int = Query(default=30),
    horizon_days: int = Query(default=30),
    location_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    if location_id is not None:
        await LocationService(LocationRepo(db)).ensure_org_location(org_id=org_id, location_id=location_id)
    svc = InventoryService(InventoryRepo(db))
    try:
        out = await svc.forecast(
            org_id=org_id,
            lookback_days=lookback_days,
            horizon_days=horizon_days,
            location_id=location_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return InventoryForecastOut.model_validate(out)
