import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.workforce_attendance_repo import WorkforceAttendanceRepo
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_leave_request_repo import WorkforceLeaveRequestRepo
from app.domain.repos.workforce_payroll_repo import WorkforcePayrollRepo
from app.domain.schemas.workforce_payroll import (
    WorkforcePayrollAdjustmentCreateIn,
    WorkforcePayrollAdjustmentOut,
    WorkforcePayrollEntryOut,
    WorkforcePayrollGenerateDraftIn,
    WorkforcePayrollPeriodActionIn,
    WorkforcePayrollPeriodCreateIn,
    WorkforcePayrollPeriodOut,
    WorkforcePayslipPreviewOut,
)
from app.domain.services.errors import NotFoundError
from app.domain.services.workforce_payslip_pdf import build_workforce_payslip_pdf_bytes
from app.domain.services.workforce_payroll_service import WorkforcePayrollService

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


def _assert_owner_role(role: str) -> None:
    if role != "OWNER":
        raise HTTPException(status_code=403, detail="Forbidden")


def _redact_entry_out(entry: WorkforcePayrollEntryOut, role: str) -> WorkforcePayrollEntryOut:
    if role in {"OWNER", "EDITOR"}:
        return entry
    return entry.model_copy(
        update={
            "base_salary": None,
            "hourly_rate": None,
            "overtime_multiplier": None,
            "payable_hours": None,
            "unpaid_leave_deduction": None,
            "gross_pay": None,
            "adjustments_total": None,
            "net_pay": None,
        }
    )


def _redact_adjustment_out(row: WorkforcePayrollAdjustmentOut, role: str) -> WorkforcePayrollAdjustmentOut:
    if role in {"OWNER", "EDITOR"}:
        return row
    return row.model_copy(update={"amount": None})


def _entry_out_from_model(row, role: str) -> WorkforcePayrollEntryOut:
    return _redact_entry_out(WorkforcePayrollEntryOut.model_validate(row, from_attributes=True), role)


def _svc(db: AsyncSession) -> WorkforcePayrollService:
    return WorkforcePayrollService(
        payroll_repo=WorkforcePayrollRepo(db),
        employee_repo=WorkforceEmployeeRepo(db),
        attendance_repo=WorkforceAttendanceRepo(db),
        leave_request_repo=WorkforceLeaveRequestRepo(db),
    )


@router.get("/periods", response_model=list[WorkforcePayrollPeriodOut])
async def list_periods(
    org_id: uuid.UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    rows = await _svc(db).list_periods(org_id=org_id, limit=limit)
    return [WorkforcePayrollPeriodOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/periods", response_model=WorkforcePayrollPeriodOut)
async def create_period(
    body: WorkforcePayrollPeriodCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).create_period(
            org_id=body.org_id,
            actor_user_id=user.id,
            start_date=body.start_date,
            end_date=body.end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, body.org_id, "workforce.payroll.period.create", "workforce_payroll_period", str(row.id), {"start_date": str(row.start_date), "end_date": str(row.end_date)})
    await db.commit()
    return WorkforcePayrollPeriodOut.model_validate(row, from_attributes=True)


@router.post("/periods/{payroll_period_id}/generate", response_model=list[WorkforcePayrollEntryOut])
async def generate(
    payroll_period_id: uuid.UUID,
    body: WorkforcePayrollGenerateDraftIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    if payroll_period_id != body.payroll_period_id:
        raise HTTPException(status_code=422, detail="Mismatched payroll_period_id")
    try:
        rows = await _svc(db).generate_draft(
            org_id=body.org_id,
            actor_user_id=user.id,
            payroll_period_id=payroll_period_id,
            include_inactive_employees=body.include_inactive_employees,
            overtime_multiplier=body.overtime_multiplier,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, body.org_id, "workforce.payroll.period.generate", "workforce_payroll_period", str(payroll_period_id), {"entries": len(rows)})
    await db.commit()
    return [_entry_out_from_model(r, ctx.role) for r in rows]


@router.get("/periods/{payroll_period_id}/entries", response_model=list[WorkforcePayrollEntryOut])
async def list_entries(
    payroll_period_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    try:
        rows = await _svc(db).list_entries(org_id=org_id, payroll_period_id=payroll_period_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_entry_out_from_model(r, ctx.role) for r in rows]


@router.post("/periods/{payroll_period_id}/approve", response_model=WorkforcePayrollPeriodOut)
async def approve(
    payroll_period_id: uuid.UUID,
    body: WorkforcePayrollPeriodActionIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).approve_period(org_id=body.org_id, actor_user_id=user.id, payroll_period_id=payroll_period_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, body.org_id, "workforce.payroll.period.approve", "workforce_payroll_period", str(row.id), {})
    await db.commit()
    return WorkforcePayrollPeriodOut.model_validate(row, from_attributes=True)


@router.post("/periods/{payroll_period_id}/mark-paid", response_model=WorkforcePayrollPeriodOut)
async def mark_paid(
    payroll_period_id: uuid.UUID,
    body: WorkforcePayrollPeriodActionIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_owner_role(ctx.role)
    try:
        row = await _svc(db).mark_paid(org_id=body.org_id, actor_user_id=user.id, payroll_period_id=payroll_period_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, body.org_id, "workforce.payroll.period.mark_paid", "workforce_payroll_period", str(row.id), {})
    await db.commit()
    return WorkforcePayrollPeriodOut.model_validate(row, from_attributes=True)


@router.get("/periods/{payroll_period_id}/export")
async def export_csv(
    payroll_period_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    try:
        csv_text = await _svc(db).export_csv(
            org_id=org_id,
            payroll_period_id=payroll_period_id,
            redact_amounts=ctx.role == "VIEWER",
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=csv_text, media_type="text/csv")


@router.post("/adjustments", response_model=WorkforcePayrollAdjustmentOut)
async def create_adjustment(
    body: WorkforcePayrollAdjustmentCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).create_adjustment(
            org_id=body.org_id,
            actor_user_id=user.id,
            payroll_period_id=body.payroll_period_id,
            payroll_entry_id=body.payroll_entry_id,
            employee_id=body.employee_id,
            kind=body.kind,
            amount=body.amount,
            label=body.label,
            notes=body.notes,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, body.org_id, "workforce.payroll.adjustment.create", "workforce_payroll_adjustment", str(row.id), {"kind": row.kind, "amount": str(row.amount)})
    await db.commit()
    return WorkforcePayrollAdjustmentOut.model_validate(row, from_attributes=True)


@router.delete("/adjustments/{adjustment_id}")
async def delete_adjustment(
    adjustment_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    payroll_period_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        await _svc(db).delete_adjustment(org_id=org_id, payroll_period_id=payroll_period_id, adjustment_id=adjustment_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, org_id, "workforce.payroll.adjustment.delete", "workforce_payroll_adjustment", str(adjustment_id), {})
    await db.commit()
    return {"ok": True}


@router.get("/entries/{entry_id}/payslip", response_model=WorkforcePayslipPreviewOut)
async def payslip_preview(
    entry_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = WorkforcePayrollRepo(db)
    entry = await repo.get_entry(org_id=org_id, entry_id=entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    period = await repo.get_period(org_id=org_id, period_id=entry.payroll_period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="Payroll period not found")
    adjustments = await repo.list_adjustments(org_id=org_id, payroll_entry_id=entry.id)
    entry_out = _entry_out_from_model(entry, ctx.role)
    adj_out = [_redact_adjustment_out(WorkforcePayrollAdjustmentOut.model_validate(a, from_attributes=True), ctx.role) for a in adjustments]
    return WorkforcePayslipPreviewOut(
        entry=entry_out,
        adjustments=adj_out,
        period=WorkforcePayrollPeriodOut.model_validate(period, from_attributes=True),
    )


@router.get("/entries/{entry_id}/payslip/pdf")
async def payslip_pdf(
    entry_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = WorkforcePayrollRepo(db)
    entry = await repo.get_entry(org_id=org_id, entry_id=entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    period = await repo.get_period(org_id=org_id, period_id=entry.payroll_period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="Payroll period not found")
    adjustments = await repo.list_adjustments(org_id=org_id, payroll_entry_id=entry.id)
    emp = await WorkforceEmployeeRepo(db).get_by_id(org_id=org_id, employee_id=entry.employee_id)
    employee_name = (
        f"{(emp.first_name or '').strip()} {(emp.last_name or '').strip()}".strip() or str(entry.employee_id)
        if emp
        else str(entry.employee_id)
    )
    redact = ctx.role == "VIEWER"
    pdf_bytes = build_workforce_payslip_pdf_bytes(
        employee_name=employee_name,
        redact=redact,
        entry=entry,
        period=period,
        adjustments=adjustments,
    )
    filename = f"payslip-{entry_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

