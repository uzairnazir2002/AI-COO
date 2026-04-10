import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.location_repo import LocationRepo
from app.domain.repos.workforce_department_repo import WorkforceDepartmentRepo
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_title_repo import WorkforceTitleRepo
from app.domain.schemas.workforce import (
    WorkforceEmployeeCreateIn,
    WorkforceEmployeeOut,
    WorkforceEmployeeUpdateIn,
)
from app.domain.services.errors import NotFoundError
from app.domain.services.location_service import LocationService
from app.domain.services.workforce_employee_service import WorkforceEmployeeService

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


def _assert_owner(role: str) -> None:
    if role != "OWNER":
        raise HTTPException(status_code=403, detail="Forbidden")


def _redact_employee_for_role(row: WorkforceEmployeeOut, role: str) -> WorkforceEmployeeOut:
    if role in {"OWNER", "EDITOR"}:
        return row
    return row.model_copy(update={"base_salary": None, "hourly_rate": None})


@router.get("", response_model=list[WorkforceEmployeeOut])
async def list_employees(
    org_id: uuid.UUID = Query(...),
    q: str | None = Query(default=None),
    department_id: uuid.UUID | None = Query(default=None),
    title_id: uuid.UUID | None = Query(default=None),
    manager_employee_id: uuid.UUID | None = Query(default=None),
    employment_status: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=5000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    svc = WorkforceEmployeeService(
        employee_repo=WorkforceEmployeeRepo(db),
        department_repo=WorkforceDepartmentRepo(db),
        title_repo=WorkforceTitleRepo(db),
    )
    try:
        rows = await svc.list_employees(
            org_id=org_id,
            include_inactive=include_inactive,
            q=q,
            department_id=department_id,
            title_id=title_id,
            manager_employee_id=manager_employee_id,
            employment_status=employment_status,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    out = [WorkforceEmployeeOut.model_validate(row, from_attributes=True) for row in rows]
    return [_redact_employee_for_role(row, ctx.role) for row in out]


@router.get("/{employee_id}", response_model=WorkforceEmployeeOut)
async def get_employee(
    employee_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    svc = WorkforceEmployeeService(
        employee_repo=WorkforceEmployeeRepo(db),
        department_repo=WorkforceDepartmentRepo(db),
        title_repo=WorkforceTitleRepo(db),
    )
    try:
        row = await svc.get_employee(org_id=org_id, employee_id=employee_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    out = WorkforceEmployeeOut.model_validate(row, from_attributes=True)
    return _redact_employee_for_role(out, ctx.role)


@router.post("", response_model=WorkforceEmployeeOut)
async def create_employee(
    body: WorkforceEmployeeCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    if body.location_id is not None:
        await LocationService(LocationRepo(db)).ensure_org_location(org_id=body.org_id, location_id=body.location_id)
    svc = WorkforceEmployeeService(
        employee_repo=WorkforceEmployeeRepo(db),
        department_repo=WorkforceDepartmentRepo(db),
        title_repo=WorkforceTitleRepo(db),
    )
    try:
        row = await svc.create_employee(
            org_id=body.org_id,
            actor_user_id=user.id,
            employee_code=body.employee_code,
            first_name=body.first_name,
            last_name=body.last_name,
            email=body.email,
            phone=body.phone,
            department_id=body.department_id,
            title_id=body.title_id,
            manager_employee_id=body.manager_employee_id,
            location_id=body.location_id,
            employment_type=body.employment_type,
            employment_status=body.employment_status,
            start_date=body.start_date,
            end_date=body.end_date,
            salary_type=body.salary_type,
            base_salary=body.base_salary,
            hourly_rate=body.hourly_rate,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "workforce.employee.create",
        "workforce_employee",
        str(row.id),
        {"employee_code": row.employee_code, "name": f"{row.first_name} {row.last_name}"},
    )
    await db.commit()
    out = WorkforceEmployeeOut.model_validate(row, from_attributes=True)
    return _redact_employee_for_role(out, ctx.role)


@router.put("/{employee_id}", response_model=WorkforceEmployeeOut)
async def update_employee(
    employee_id: uuid.UUID,
    body: WorkforceEmployeeUpdateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    fields_set = set(body.model_fields_set)
    if "location_id" in fields_set:
        if body.location_id is not None:
            await LocationService(LocationRepo(db)).ensure_org_location(
                org_id=body.org_id, location_id=body.location_id
            )
    svc = WorkforceEmployeeService(
        employee_repo=WorkforceEmployeeRepo(db),
        department_repo=WorkforceDepartmentRepo(db),
        title_repo=WorkforceTitleRepo(db),
    )
    try:
        row = await svc.update_employee(
            org_id=body.org_id,
            employee_id=employee_id,
            fields_set=fields_set,
            employee_code=body.employee_code,
            first_name=body.first_name,
            last_name=body.last_name,
            email=body.email,
            phone=body.phone,
            department_id=body.department_id,
            title_id=body.title_id,
            manager_employee_id=body.manager_employee_id,
            location_id=body.location_id,
            employment_type=body.employment_type,
            employment_status=body.employment_status,
            start_date=body.start_date,
            end_date=body.end_date,
            salary_type=body.salary_type,
            base_salary=body.base_salary,
            hourly_rate=body.hourly_rate,
            is_active=body.is_active,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "workforce.employee.update",
        "workforce_employee",
        str(row.id),
        {"fields": sorted(fields_set)},
    )
    await db.commit()
    out = WorkforceEmployeeOut.model_validate(row, from_attributes=True)
    return _redact_employee_for_role(out, ctx.role)


@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    _assert_owner(ctx.role)
    svc = WorkforceEmployeeService(
        employee_repo=WorkforceEmployeeRepo(db),
        department_repo=WorkforceDepartmentRepo(db),
        title_repo=WorkforceTitleRepo(db),
    )
    try:
        row = await svc.deactivate_employee(org_id=org_id, employee_id=employee_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        org_id,
        "workforce.employee.deactivate",
        "workforce_employee",
        str(row.id),
        {"employee_code": row.employee_code, "name": f"{row.first_name} {row.last_name}"},
    )
    await db.commit()
    return {"ok": True}

