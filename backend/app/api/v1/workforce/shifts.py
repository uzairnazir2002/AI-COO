import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_sensitive_reauth, resolve_workforce_org_id_from_request
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_shift_repo import WorkforceShiftRepo
from app.domain.schemas.workforce_attendance import (
    WorkforceShiftAssignmentCreateIn,
    WorkforceShiftAssignmentOut,
    WorkforceShiftCreateIn,
    WorkforceShiftOut,
    WorkforceShiftUpdateIn,
)
from app.domain.services.errors import NotFoundError
from app.domain.services.workforce_shift_service import WorkforceShiftService

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("", response_model=list[WorkforceShiftOut])
async def list_shifts(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    await get_org_context(org_id=resolved_org_id, user=user, db=db)
    svc = WorkforceShiftService(shift_repo=WorkforceShiftRepo(db), employee_repo=WorkforceEmployeeRepo(db))
    rows = await svc.list_shifts(org_id=resolved_org_id, include_inactive=include_inactive)
    return [WorkforceShiftOut.model_validate(row, from_attributes=True) for row in rows]


@router.post("", response_model=WorkforceShiftOut)
async def create_shift(
    request: Request,
    body: WorkforceShiftCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceShiftService(shift_repo=WorkforceShiftRepo(db), employee_repo=WorkforceEmployeeRepo(db))
    try:
        row = await svc.create_shift(
            org_id=resolved_org_id,
            actor_user_id=user.id,
            name=body.name,
            start_time=body.start_time,
            end_time=body.end_time,
            grace_minutes=body.grace_minutes,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.shift.create",
        "workforce_shift",
        str(row.id),
        {"name": row.name, "start_time": str(row.start_time), "end_time": str(row.end_time)},
    )
    await db.commit()
    return WorkforceShiftOut.model_validate(row, from_attributes=True)


@router.put("/{shift_id}", response_model=WorkforceShiftOut)
async def update_shift(
    request: Request,
    shift_id: uuid.UUID,
    body: WorkforceShiftUpdateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceShiftService(shift_repo=WorkforceShiftRepo(db), employee_repo=WorkforceEmployeeRepo(db))
    try:
        row = await svc.update_shift(
            org_id=resolved_org_id,
            shift_id=shift_id,
            name=body.name,
            start_time=body.start_time,
            end_time=body.end_time,
            grace_minutes=body.grace_minutes,
            is_active=body.is_active,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.shift.update",
        "workforce_shift",
        str(row.id),
        {"name": row.name, "is_active": row.is_active},
    )
    await db.commit()
    return WorkforceShiftOut.model_validate(row, from_attributes=True)


@router.delete("/{shift_id}")
async def delete_shift(
    request: Request,
    shift_id: uuid.UUID,
    org_id: uuid.UUID | None = Query(default=None),
    _reauth: None = Depends(require_sensitive_reauth()),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceShiftService(shift_repo=WorkforceShiftRepo(db), employee_repo=WorkforceEmployeeRepo(db))
    try:
        row = await svc.deactivate_shift(org_id=resolved_org_id, shift_id=shift_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.shift.deactivate",
        "workforce_shift",
        str(row.id),
        {"name": row.name},
    )
    await db.commit()
    return {"ok": True}


@router.get("/assignments", response_model=list[WorkforceShiftAssignmentOut])
async def list_assignments(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    shift_id: uuid.UUID | None = Query(default=None),
    as_of: date | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    await get_org_context(org_id=resolved_org_id, user=user, db=db)
    svc = WorkforceShiftService(shift_repo=WorkforceShiftRepo(db), employee_repo=WorkforceEmployeeRepo(db))
    rows = await svc.list_assignments(org_id=resolved_org_id, employee_id=employee_id, shift_id=shift_id, as_of=as_of, limit=limit)
    return [WorkforceShiftAssignmentOut.model_validate(row, from_attributes=True) for row in rows]


@router.post("/assignments", response_model=WorkforceShiftAssignmentOut)
async def create_assignment(
    request: Request,
    body: WorkforceShiftAssignmentCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceShiftService(shift_repo=WorkforceShiftRepo(db), employee_repo=WorkforceEmployeeRepo(db))
    try:
        row = await svc.assign_shift(
            org_id=resolved_org_id,
            actor_user_id=user.id,
            employee_id=body.employee_id,
            shift_id=body.shift_id,
            effective_from=body.effective_from,
            effective_to=body.effective_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.shift_assignment.create",
        "workforce_shift_assignment",
        str(row.id),
        {"employee_id": str(body.employee_id), "shift_id": str(body.shift_id), "effective_from": str(body.effective_from)},
    )
    await db.commit()
    return WorkforceShiftAssignmentOut.model_validate(row, from_attributes=True)

