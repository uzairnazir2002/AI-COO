import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, resolve_workforce_org_id_from_request
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.workforce_attendance_repo import WorkforceAttendanceRepo
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_shift_repo import WorkforceShiftRepo
from app.domain.schemas.workforce_attendance import (
    WorkforceAttendanceCorrectionOut,
    WorkforceAttendanceCorrectionRequestIn,
    WorkforceAttendanceCorrectionReviewIn,
)
from app.domain.services.errors import NotFoundError
from app.domain.services.workforce_access_policy import build_workforce_access_scope
from app.domain.services.workforce_attendance_service import WorkforceAttendanceService

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR", "MANAGER"}:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("", response_model=list[WorkforceAttendanceCorrectionOut])
async def list_corrections(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    access = await build_workforce_access_scope(
        db=db, org_id=resolved_org_id, role=ctx.role, actor_user_id=user.id, actor_email=user.email
    )
    repo = WorkforceAttendanceRepo(db)
    rows = await repo.list_corrections(org_id=resolved_org_id, status=status, employee_id=employee_id, limit=limit)
    out = [WorkforceAttendanceCorrectionOut.model_validate(row, from_attributes=True) for row in rows]
    return [row for row in out if access.can_access_employee(row.employee_id)]


@router.post("", response_model=WorkforceAttendanceCorrectionOut)
async def request_correction(
    request: Request,
    body: WorkforceAttendanceCorrectionRequestIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    access = await build_workforce_access_scope(
        db=db, org_id=resolved_org_id, role=ctx.role, actor_user_id=user.id, actor_email=user.email
    )
    svc = WorkforceAttendanceService(
        attendance_repo=WorkforceAttendanceRepo(db),
        employee_repo=WorkforceEmployeeRepo(db),
        shift_repo=WorkforceShiftRepo(db),
    )
    try:
        row = await svc.request_correction(
            org_id=resolved_org_id,
            actor_user_id=user.id,
            attendance_record_id=body.attendance_record_id,
            reason=body.reason,
            proposed_clock_in_at=body.proposed_clock_in_at,
            proposed_clock_out_at=body.proposed_clock_out_at,
            proposed_status=body.proposed_status,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not access.can_access_employee(row.employee_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.attendance.correction.request",
        "workforce_attendance_correction",
        str(row.id),
        {"record_id": str(body.attendance_record_id), "employee_id": str(row.employee_id)},
    )
    await db.commit()
    return WorkforceAttendanceCorrectionOut.model_validate(row, from_attributes=True)


@router.post("/{correction_id}/review", response_model=WorkforceAttendanceCorrectionOut)
async def review_correction(
    request: Request,
    correction_id: uuid.UUID,
    body: WorkforceAttendanceCorrectionReviewIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    access = await build_workforce_access_scope(
        db=db, org_id=resolved_org_id, role=ctx.role, actor_user_id=user.id, actor_email=user.email
    )
    svc = WorkforceAttendanceService(
        attendance_repo=WorkforceAttendanceRepo(db),
        employee_repo=WorkforceEmployeeRepo(db),
        shift_repo=WorkforceShiftRepo(db),
    )
    try:
        row = await svc.review_correction(
            org_id=resolved_org_id,
            actor_user_id=user.id,
            correction_id=correction_id,
            status=body.status,
            reviewer_note=body.reviewer_note,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not access.can_access_employee(row.employee_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.attendance.correction.review",
        "workforce_attendance_correction",
        str(row.id),
        {"status": row.status, "employee_id": str(row.employee_id), "record_id": str(row.attendance_record_id)},
    )
    await db.commit()
    return WorkforceAttendanceCorrectionOut.model_validate(row, from_attributes=True)

