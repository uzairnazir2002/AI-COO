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
from app.domain.repos.workforce_shift_repo import WorkforceShiftRepo
from app.domain.schemas.workforce_attendance import (
    WorkforceAttendanceCalendarOut,
    WorkforceAttendanceClockInIn,
    WorkforceAttendanceClockOutIn,
    WorkforceAttendanceDailyOut,
    WorkforceAttendanceManualIn,
    WorkforceAttendanceOut,
)
from app.domain.services.workforce_attendance_service import WorkforceAttendanceService

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/daily", response_model=WorkforceAttendanceDailyOut)
async def daily(
    org_id: uuid.UUID = Query(...),
    date_value: date = Query(..., alias="date"),
    employee_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    svc = WorkforceAttendanceService(
        attendance_repo=WorkforceAttendanceRepo(db),
        employee_repo=WorkforceEmployeeRepo(db),
        shift_repo=WorkforceShiftRepo(db),
    )
    rows = await svc.daily_view(org_id=org_id, day=date_value, employee_id=employee_id)
    items = [WorkforceAttendanceOut.model_validate(row, from_attributes=True) for row in rows]
    return WorkforceAttendanceDailyOut(org_id=org_id, date=date_value, items=items)


@router.get("/calendar", response_model=WorkforceAttendanceCalendarOut)
async def calendar(
    org_id: uuid.UUID = Query(...),
    month: str = Query(..., description="Month in YYYY-MM"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    svc = WorkforceAttendanceService(
        attendance_repo=WorkforceAttendanceRepo(db),
        employee_repo=WorkforceEmployeeRepo(db),
        shift_repo=WorkforceShiftRepo(db),
    )
    try:
        out = await svc.calendar_month(org_id=org_id, month=month)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return WorkforceAttendanceCalendarOut.model_validate(out)


@router.post("/clock-in", response_model=WorkforceAttendanceOut)
async def clock_in(
    body: WorkforceAttendanceClockInIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceAttendanceService(
        attendance_repo=WorkforceAttendanceRepo(db),
        employee_repo=WorkforceEmployeeRepo(db),
        shift_repo=WorkforceShiftRepo(db),
    )
    try:
        row = await svc.clock_in(org_id=body.org_id, actor_user_id=user.id, employee_id=body.employee_id, at=body.at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "workforce.attendance.clock_in",
        "workforce_attendance_record",
        str(row.id),
        {"employee_id": str(body.employee_id), "work_date": str(row.work_date)},
    )
    await db.commit()
    return WorkforceAttendanceOut.model_validate(row, from_attributes=True)


@router.post("/clock-out", response_model=WorkforceAttendanceOut)
async def clock_out(
    body: WorkforceAttendanceClockOutIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceAttendanceService(
        attendance_repo=WorkforceAttendanceRepo(db),
        employee_repo=WorkforceEmployeeRepo(db),
        shift_repo=WorkforceShiftRepo(db),
    )
    try:
        row = await svc.clock_out(org_id=body.org_id, actor_user_id=user.id, employee_id=body.employee_id, at=body.at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "workforce.attendance.clock_out",
        "workforce_attendance_record",
        str(row.id),
        {"employee_id": str(body.employee_id), "work_date": str(row.work_date)},
    )
    await db.commit()
    return WorkforceAttendanceOut.model_validate(row, from_attributes=True)


@router.post("/manual", response_model=WorkforceAttendanceOut)
async def manual(
    body: WorkforceAttendanceManualIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceAttendanceService(
        attendance_repo=WorkforceAttendanceRepo(db),
        employee_repo=WorkforceEmployeeRepo(db),
        shift_repo=WorkforceShiftRepo(db),
    )
    try:
        row = await svc.manual_entry(
            org_id=body.org_id,
            actor_user_id=user.id,
            employee_id=body.employee_id,
            work_date=body.work_date,
            status=body.status,
            clock_in_at=body.clock_in_at,
            clock_out_at=body.clock_out_at,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "workforce.attendance.manual",
        "workforce_attendance_record",
        str(row.id),
        {"employee_id": str(body.employee_id), "work_date": str(row.work_date), "status": row.status},
    )
    await db.commit()
    return WorkforceAttendanceOut.model_validate(row, from_attributes=True)

