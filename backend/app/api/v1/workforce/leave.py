import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.workforce_attendance_repo import WorkforceAttendanceRepo
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_leave_balance_repo import WorkforceLeaveBalanceRepo
from app.domain.repos.workforce_leave_request_repo import WorkforceLeaveRequestRepo
from app.domain.repos.workforce_leave_type_repo import WorkforceLeaveTypeRepo
from app.domain.schemas.workforce_leave import (
    WorkforceLeaveBalanceAllocateIn,
    WorkforceLeaveBalanceOut,
    WorkforceLeaveRequestCreateIn,
    WorkforceLeaveRequestDecisionIn,
    WorkforceLeaveRequestOut,
    WorkforceLeaveTypeCreateIn,
    WorkforceLeaveTypeOut,
    WorkforceLeaveTypeUpdateIn,
)
from app.domain.services.errors import NotFoundError
from app.domain.services.workforce_leave_service import WorkforceLeaveService

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


def _assert_owner(role: str) -> None:
    if role != "OWNER":
        raise HTTPException(status_code=403, detail="Forbidden")


def _svc(db: AsyncSession) -> WorkforceLeaveService:
    return WorkforceLeaveService(
        leave_type_repo=WorkforceLeaveTypeRepo(db),
        leave_balance_repo=WorkforceLeaveBalanceRepo(db),
        leave_request_repo=WorkforceLeaveRequestRepo(db),
        employee_repo=WorkforceEmployeeRepo(db),
        attendance_repo=WorkforceAttendanceRepo(db),
    )


# Leave types
@router.get("/types", response_model=list[WorkforceLeaveTypeOut])
async def list_leave_types(
    org_id: uuid.UUID = Query(...),
    include_inactive: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    rows = await _svc(db).list_leave_types(org_id=org_id, include_inactive=include_inactive)
    return [WorkforceLeaveTypeOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/types", response_model=WorkforceLeaveTypeOut)
async def create_leave_type(
    body: WorkforceLeaveTypeCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).create_leave_type(
            org_id=body.org_id,
            actor_user_id=user.id,
            name=body.name,
            code=body.code,
            is_paid=body.is_paid,
            requires_approval=body.requires_approval,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, body.org_id, "workforce.leave_type.create", "workforce_leave_type", str(row.id), {"name": row.name})
    await db.commit()
    return WorkforceLeaveTypeOut.model_validate(row, from_attributes=True)


@router.put("/types/{leave_type_id}", response_model=WorkforceLeaveTypeOut)
async def update_leave_type(
    leave_type_id: uuid.UUID,
    body: WorkforceLeaveTypeUpdateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).update_leave_type(
            org_id=body.org_id,
            leave_type_id=leave_type_id,
            name=body.name,
            code=body.code,
            is_paid=body.is_paid,
            requires_approval=body.requires_approval,
            is_active=body.is_active,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, body.org_id, "workforce.leave_type.update", "workforce_leave_type", str(row.id), {})
    await db.commit()
    return WorkforceLeaveTypeOut.model_validate(row, from_attributes=True)


@router.delete("/types/{leave_type_id}")
async def delete_leave_type(
    leave_type_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    _assert_owner(ctx.role)
    try:
        row = await _svc(db).deactivate_leave_type(org_id=org_id, leave_type_id=leave_type_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, org_id, "workforce.leave_type.deactivate", "workforce_leave_type", str(row.id), {"name": row.name})
    await db.commit()
    return {"ok": True}


# Balances
@router.get("/balances", response_model=list[WorkforceLeaveBalanceOut])
async def list_balances(
    org_id: uuid.UUID = Query(...),
    employee_id: uuid.UUID | None = Query(default=None),
    year: int | None = Query(default=None),
    limit: int = Query(default=2000, ge=1, le=5000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    rows = await _svc(db).list_balances(org_id=org_id, employee_id=employee_id, year=year, limit=limit)
    return [WorkforceLeaveBalanceOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/balances/allocate", response_model=WorkforceLeaveBalanceOut)
async def allocate_balance(
    body: WorkforceLeaveBalanceAllocateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).allocate_balance(
            org_id=body.org_id,
            actor_user_id=user.id,
            employee_id=body.employee_id,
            leave_type_id=body.leave_type_id,
            year=body.year,
            allocated_days=body.allocated_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, body.org_id, "workforce.leave_balance.allocate", "workforce_leave_balance", str(row.id), {"year": row.year})
    await db.commit()
    return WorkforceLeaveBalanceOut.model_validate(row, from_attributes=True)


# Requests
@router.get("/requests", response_model=list[WorkforceLeaveRequestOut])
async def list_requests(
    org_id: uuid.UUID = Query(...),
    status: str | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    rows = await _svc(db).list_requests(
        org_id=org_id, status=status, employee_id=employee_id, from_date=from_date, to_date=to_date, limit=limit
    )
    return [WorkforceLeaveRequestOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/requests", response_model=WorkforceLeaveRequestOut)
async def create_request(
    body: WorkforceLeaveRequestCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).create_request(
            org_id=body.org_id,
            actor_user_id=user.id,
            employee_id=body.employee_id,
            leave_type_id=body.leave_type_id,
            start_date=body.start_date,
            end_date=body.end_date,
            days=body.days,
            reason=body.reason,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "workforce.leave_request.create",
        "workforce_leave_request",
        str(row.id),
        {"employee_id": str(row.employee_id), "start_date": str(row.start_date), "end_date": str(row.end_date), "days": str(row.days)},
    )
    await db.commit()
    return WorkforceLeaveRequestOut.model_validate(row, from_attributes=True)


@router.post("/requests/{request_id}/decision", response_model=WorkforceLeaveRequestOut)
async def decide_request(
    request_id: uuid.UUID,
    body: WorkforceLeaveRequestDecisionIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).decide_request(
            org_id=body.org_id,
            actor_user_id=user.id,
            request_id=request_id,
            status=body.status,
            reviewer_note=body.reviewer_note,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "workforce.leave_request.decision",
        "workforce_leave_request",
        str(row.id),
        {"status": row.status},
    )
    await db.commit()
    return WorkforceLeaveRequestOut.model_validate(row, from_attributes=True)

