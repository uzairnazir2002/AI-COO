import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_sensitive_reauth, resolve_workforce_org_id_from_request
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.workforce_department_repo import WorkforceDepartmentRepo
from app.domain.schemas.workforce import (
    WorkforceDepartmentCreateIn,
    WorkforceDepartmentOut,
    WorkforceDepartmentUpdateIn,
)
from app.domain.services.errors import NotFoundError
from app.domain.services.workforce_department_service import WorkforceDepartmentService

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("", response_model=list[WorkforceDepartmentOut])
async def list_departments(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    await get_org_context(org_id=resolved_org_id, user=user, db=db)
    rows = await WorkforceDepartmentService(WorkforceDepartmentRepo(db)).list_departments(
        org_id=resolved_org_id, include_inactive=include_inactive
    )
    return [WorkforceDepartmentOut.model_validate(row, from_attributes=True) for row in rows]


@router.post("", response_model=WorkforceDepartmentOut)
async def create_department(
    request: Request,
    body: WorkforceDepartmentCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceDepartmentService(WorkforceDepartmentRepo(db))
    try:
        row = await svc.create_department(
            org_id=resolved_org_id,
            actor_user_id=user.id,
            name=body.name,
            code=body.code,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.department.create",
        "workforce_department",
        str(row.id),
        {"name": row.name, "code": row.code, "is_active": row.is_active},
    )
    await db.commit()
    return WorkforceDepartmentOut.model_validate(row, from_attributes=True)


@router.put("/{department_id}", response_model=WorkforceDepartmentOut)
async def update_department(
    request: Request,
    department_id: uuid.UUID,
    body: WorkforceDepartmentUpdateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceDepartmentService(WorkforceDepartmentRepo(db))
    try:
        row = await svc.update_department(
            org_id=resolved_org_id,
            department_id=department_id,
            name=body.name,
            code=body.code,
            is_active=body.is_active,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.department.update",
        "workforce_department",
        str(row.id),
        {"name": row.name, "code": row.code, "is_active": row.is_active},
    )
    await db.commit()
    return WorkforceDepartmentOut.model_validate(row, from_attributes=True)


@router.delete("/{department_id}")
async def delete_department(
    request: Request,
    department_id: uuid.UUID,
    org_id: uuid.UUID | None = Query(default=None),
    _reauth: None = Depends(require_sensitive_reauth()),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceDepartmentService(WorkforceDepartmentRepo(db))
    try:
        row = await svc.deactivate_department(org_id=resolved_org_id, department_id=department_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.department.deactivate",
        "workforce_department",
        str(row.id),
        {"name": row.name},
    )
    await db.commit()
    return {"ok": True}

