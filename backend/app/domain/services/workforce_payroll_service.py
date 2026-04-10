from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from app.domain.models.workforce_payroll_adjustment import WorkforcePayrollAdjustment
from app.domain.models.workforce_payroll_entry import WorkforcePayrollEntry
from app.domain.models.workforce_payroll_period import WorkforcePayrollPeriod
from app.domain.repos.workforce_attendance_repo import WorkforceAttendanceRepo
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_leave_request_repo import WorkforceLeaveRequestRepo
from app.domain.repos.workforce_payroll_repo import WorkforcePayrollRepo
from app.domain.services.errors import NotFoundError
from app.domain.services.workforce_announcement_automation import (
    AUTOMATION_KEY_PAYROLL_PERIOD_APPROVED,
    AUTOMATION_KEY_PAYROLL_PERIOD_PAID,
    try_emit_automation_announcement,
)


VALID_PERIOD_STATUSES = {"DRAFT", "APPROVED", "PAID"}
VALID_ADJUSTMENT_KINDS = {"BONUS", "DEDUCTION", "ADVANCE", "REIMBURSEMENT"}


def _q2(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class PayrollTotals:
    gross_pay: Decimal
    adjustments_total: Decimal
    net_pay: Decimal


class WorkforcePayrollService:
    def __init__(
        self,
        *,
        payroll_repo: WorkforcePayrollRepo,
        employee_repo: WorkforceEmployeeRepo,
        attendance_repo: WorkforceAttendanceRepo,
        leave_request_repo: WorkforceLeaveRequestRepo,
    ):
        self.payroll_repo = payroll_repo
        self.employee_repo = employee_repo
        self.attendance_repo = attendance_repo
        self.leave_request_repo = leave_request_repo

    async def list_periods(self, *, org_id: uuid.UUID, limit: int = 50) -> list[WorkforcePayrollPeriod]:
        return await self.payroll_repo.list_periods(org_id=org_id, limit=limit)

    async def create_period(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> WorkforcePayrollPeriod:
        if end_date < start_date:
            raise ValueError("end_date cannot be before start_date")
        return await self.payroll_repo.create_period(
            WorkforcePayrollPeriod(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                start_date=start_date,
                end_date=end_date,
                status="DRAFT",
            )
        )

    async def generate_draft(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payroll_period_id: uuid.UUID,
        include_inactive_employees: bool,
        overtime_multiplier: Decimal,
    ) -> list[WorkforcePayrollEntry]:
        period = await self.payroll_repo.get_period(org_id=org_id, period_id=payroll_period_id)
        if period is None:
            raise NotFoundError("Payroll period not found")
        if period.status != "DRAFT":
            raise ValueError("Can only generate draft entries for a DRAFT period")

        employees = await self.employee_repo.list_by_org(org_id=org_id, include_inactive=include_inactive_employees, limit=5000)
        out: list[WorkforcePayrollEntry] = []
        for emp in employees:
            worked_minutes, overtime_minutes = await self.payroll_repo.attendance_sum_for_employee(
                attendance_repo=self.attendance_repo,
                org_id=org_id,
                employee_id=emp.id,
                start_date=period.start_date,
                end_date=period.end_date,
            )

            payable_hours = _q2(Decimal(worked_minutes) / Decimal(60)) if worked_minutes > 0 else Decimal("0")

            entry = await self.payroll_repo.get_entry_for_employee(
                org_id=org_id, payroll_period_id=period.id, employee_id=emp.id
            )
            if entry is None:
                entry = WorkforcePayrollEntry(
                    org_id=org_id,
                    created_by_user_id=actor_user_id,
                    payroll_period_id=period.id,
                    employee_id=emp.id,
                )

            entry.salary_type = (emp.salary_type or "SALARIED").strip().upper()
            entry.base_salary = emp.base_salary
            entry.hourly_rate = emp.hourly_rate
            entry.overtime_multiplier = _q2(Decimal(overtime_multiplier))
            entry.worked_minutes = int(worked_minutes)
            entry.overtime_minutes = int(overtime_minutes)
            entry.payable_hours = payable_hours
            entry.status = "DRAFT"
            entry.is_locked = False

            st = entry.salary_type.strip().upper()
            if st == "SALARIED":
                base = _q2(Decimal(emp.base_salary or Decimal("0")))
                entry.unpaid_leave_deduction = await self._salaried_unpaid_leave_deduction(
                    org_id=org_id,
                    employee_id=emp.id,
                    period_start=period.start_date,
                    period_end=period.end_date,
                    base_salary=base,
                )
            else:
                entry.unpaid_leave_deduction = Decimal("0")

            adjustments = await self.payroll_repo.list_adjustments(org_id=org_id, payroll_entry_id=entry.id) if getattr(entry, "id", None) else []
            totals = self._compute_totals(entry=entry, adjustments=adjustments)
            entry.gross_pay = totals.gross_pay
            entry.adjustments_total = totals.adjustments_total
            entry.net_pay = totals.net_pay

            entry = await self.payroll_repo.upsert_entry(entry)
            out.append(entry)
        return out

    async def _salaried_unpaid_leave_deduction(
        self,
        *,
        org_id: uuid.UUID,
        employee_id: uuid.UUID,
        period_start: date,
        period_end: date,
        base_salary: Decimal,
    ) -> Decimal:
        if base_salary <= 0:
            return Decimal("0")
        unpaid_days = await self.leave_request_repo.sum_unpaid_leave_overlap_days_in_period(
            org_id=org_id,
            employee_id=employee_id,
            period_start=period_start,
            period_end=period_end,
        )
        if unpaid_days <= 0:
            return Decimal("0")
        period_days = (period_end - period_start).days + 1
        if period_days <= 0:
            return Decimal("0")
        daily = base_salary / Decimal(period_days)
        deduction = _q2(daily * unpaid_days)
        return min(deduction, base_salary)

    def _compute_totals(self, *, entry: WorkforcePayrollEntry, adjustments: list[WorkforcePayrollAdjustment]) -> PayrollTotals:
        gross = Decimal("0")
        salary_type = (entry.salary_type or "SALARIED").strip().upper()
        if salary_type == "SALARIED":
            base = _q2(Decimal(entry.base_salary or Decimal("0")))
            uld = _q2(Decimal(entry.unpaid_leave_deduction or Decimal("0")))
            gross = _q2(max(Decimal("0"), base - uld))
        elif salary_type == "HOURLY":
            rate = Decimal(entry.hourly_rate or Decimal("0"))
            overtime_hours = _q2(Decimal(entry.overtime_minutes or 0) / Decimal(60))
            total_hours = _q2(Decimal(entry.worked_minutes or 0) / Decimal(60))
            normal_hours = max(Decimal("0"), total_hours - overtime_hours)
            gross = _q2((normal_hours * rate) + (overtime_hours * rate * Decimal(entry.overtime_multiplier or Decimal("1.5"))))
        else:
            gross = Decimal("0")

        adj_total = Decimal("0")
        for a in adjustments:
            kind = (a.kind or "").strip().upper()
            amt = Decimal(a.amount or Decimal("0"))
            if kind in {"BONUS", "REIMBURSEMENT"}:
                adj_total += amt
            elif kind in {"DEDUCTION", "ADVANCE"}:
                adj_total -= amt
        adj_total = _q2(adj_total)
        net = _q2(gross + adj_total)
        return PayrollTotals(gross_pay=gross, adjustments_total=adj_total, net_pay=net)

    async def list_entries(self, *, org_id: uuid.UUID, payroll_period_id: uuid.UUID) -> list[WorkforcePayrollEntry]:
        period = await self.payroll_repo.get_period(org_id=org_id, period_id=payroll_period_id)
        if period is None:
            raise NotFoundError("Payroll period not found")
        return await self.payroll_repo.list_entries(org_id=org_id, payroll_period_id=payroll_period_id)

    async def create_adjustment(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payroll_period_id: uuid.UUID,
        payroll_entry_id: uuid.UUID,
        employee_id: uuid.UUID,
        kind: str,
        amount: Decimal,
        label: str | None,
        notes: str | None,
    ) -> WorkforcePayrollAdjustment:
        period = await self.payroll_repo.get_period(org_id=org_id, period_id=payroll_period_id)
        if period is None:
            raise NotFoundError("Payroll period not found")
        if period.status != "DRAFT":
            raise ValueError("Adjustments can only be changed for DRAFT periods")
        entry = await self.payroll_repo.get_entry(org_id=org_id, entry_id=payroll_entry_id)
        if entry is None or entry.payroll_period_id != payroll_period_id or entry.employee_id != employee_id:
            raise NotFoundError("Payroll entry not found")
        k = kind.strip().upper()
        if k not in VALID_ADJUSTMENT_KINDS:
            raise ValueError("Unsupported adjustment kind")
        adj = await self.payroll_repo.create_adjustment(
            WorkforcePayrollAdjustment(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                payroll_period_id=payroll_period_id,
                payroll_entry_id=payroll_entry_id,
                employee_id=employee_id,
                kind=k,
                amount=_q2(Decimal(amount)),
                label=label.strip() if isinstance(label, str) and label.strip() else None,
                notes=notes.strip() if isinstance(notes, str) and notes.strip() else None,
            )
        )
        # Recompute entry totals
        adjustments = await self.payroll_repo.list_adjustments(org_id=org_id, payroll_entry_id=entry.id)
        totals = self._compute_totals(entry=entry, adjustments=adjustments)
        entry.adjustments_total = totals.adjustments_total
        entry.net_pay = totals.net_pay
        entry.gross_pay = totals.gross_pay
        await self.payroll_repo.upsert_entry(entry)
        return adj

    async def delete_adjustment(self, *, org_id: uuid.UUID, payroll_period_id: uuid.UUID, adjustment_id: uuid.UUID) -> None:
        period = await self.payroll_repo.get_period(org_id=org_id, period_id=payroll_period_id)
        if period is None:
            raise NotFoundError("Payroll period not found")
        if period.status != "DRAFT":
            raise ValueError("Adjustments can only be changed for DRAFT periods")
        adj = await self.payroll_repo.get_adjustment(org_id=org_id, adjustment_id=adjustment_id)
        if adj is None or adj.payroll_period_id != payroll_period_id:
            raise NotFoundError("Adjustment not found")
        entry = await self.payroll_repo.get_entry(org_id=org_id, entry_id=adj.payroll_entry_id)
        await self.payroll_repo.delete_adjustment(adj)
        if entry is not None:
            adjustments = await self.payroll_repo.list_adjustments(org_id=org_id, payroll_entry_id=entry.id)
            totals = self._compute_totals(entry=entry, adjustments=adjustments)
            entry.adjustments_total = totals.adjustments_total
            entry.net_pay = totals.net_pay
            entry.gross_pay = totals.gross_pay
            await self.payroll_repo.upsert_entry(entry)

    async def approve_period(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, payroll_period_id: uuid.UUID) -> WorkforcePayrollPeriod:
        period = await self.payroll_repo.get_period(org_id=org_id, period_id=payroll_period_id)
        if period is None:
            raise NotFoundError("Payroll period not found")
        if period.status != "DRAFT":
            raise ValueError("Only DRAFT periods can be approved")
        period.status = "APPROVED"
        period.approved_by_user_id = actor_user_id
        period.approved_at = datetime.now(tz=timezone.utc)
        await self.payroll_repo.update_period(period)
        entries = await self.payroll_repo.list_entries(org_id=org_id, payroll_period_id=period.id)
        for e in entries:
            e.status = "APPROVED"
            e.is_locked = True
            await self.payroll_repo.upsert_entry(e)
        await try_emit_automation_announcement(
            self.payroll_repo.db,
            org_id=org_id,
            actor_user_id=actor_user_id,
            automation_key=AUTOMATION_KEY_PAYROLL_PERIOD_APPROVED,
            dedupe_key=f"PAYROLL_APPROVED:{payroll_period_id}",
            variables={
                "period_start": str(period.start_date),
                "period_end": str(period.end_date),
                "period_label": f"{period.start_date} – {period.end_date}",
            },
        )
        return period

    async def mark_paid(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, payroll_period_id: uuid.UUID) -> WorkforcePayrollPeriod:
        period = await self.payroll_repo.get_period(org_id=org_id, period_id=payroll_period_id)
        if period is None:
            raise NotFoundError("Payroll period not found")
        if period.status != "APPROVED":
            raise ValueError("Only APPROVED periods can be marked paid")
        period.status = "PAID"
        period.paid_by_user_id = actor_user_id
        period.paid_at = datetime.now(tz=timezone.utc)
        await self.payroll_repo.update_period(period)
        entries = await self.payroll_repo.list_entries(org_id=org_id, payroll_period_id=period.id)
        for e in entries:
            e.status = "PAID"
            e.is_locked = True
            await self.payroll_repo.upsert_entry(e)
        await try_emit_automation_announcement(
            self.payroll_repo.db,
            org_id=org_id,
            actor_user_id=actor_user_id,
            automation_key=AUTOMATION_KEY_PAYROLL_PERIOD_PAID,
            dedupe_key=f"PAYROLL_PAID:{payroll_period_id}",
            variables={
                "period_start": str(period.start_date),
                "period_end": str(period.end_date),
                "period_label": f"{period.start_date} – {period.end_date}",
            },
        )
        return period

    async def export_csv(self, *, org_id: uuid.UUID, payroll_period_id: uuid.UUID, redact_amounts: bool = False) -> str:
        entries = await self.list_entries(org_id=org_id, payroll_period_id=payroll_period_id)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(
            [
                "employee_id",
                "salary_type",
                "payable_hours",
                "overtime_minutes",
                "base_salary",
                "unpaid_leave_deduction",
                "gross_pay",
                "adjustments_total",
                "net_pay",
                "status",
            ]
        )
        for e in entries:
            if redact_amounts:
                w.writerow(
                    [
                        str(e.employee_id),
                        e.salary_type,
                        "",
                        int(e.overtime_minutes),
                        "",
                        "",
                        "",
                        "",
                        "",
                        e.status,
                    ]
                )
            else:
                w.writerow(
                    [
                        str(e.employee_id),
                        e.salary_type,
                        str(e.payable_hours),
                        int(e.overtime_minutes),
                        "" if e.base_salary is None else str(e.base_salary),
                        str(e.unpaid_leave_deduction),
                        str(e.gross_pay),
                        str(e.adjustments_total),
                        str(e.net_pay),
                        e.status,
                    ]
                )
        return buf.getvalue()

