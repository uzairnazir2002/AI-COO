from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Integer, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_announcement import WorkforceAnnouncement
from app.domain.models.workforce_announcement_receipt import WorkforceAnnouncementReceipt
from app.domain.models.workforce_attendance_record import WorkforceAttendanceRecord
from app.domain.models.workforce_department import WorkforceDepartment
from app.domain.models.workforce_employee import WorkforceEmployee
from app.domain.models.workforce_leave_request import WorkforceLeaveRequest
from app.domain.models.workforce_payroll_entry import WorkforcePayrollEntry
from app.domain.models.workforce_payroll_period import WorkforcePayrollPeriod
from app.domain.schemas.workforce_intelligence import (
    WorkforceAttendanceSummaryOut,
    WorkforceDashboardIntelOut,
    WorkforceDepartmentHeadcountOut,
    WorkforceLaborCostPeriodOut,
    WorkforceLeaveSummaryOut,
    WorkforcePayrollSummaryOut,
    WorkforceReportsSummaryOut,
)


class WorkforceIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def dashboard_intelligence(self, *, org_id: uuid.UUID, as_of: date) -> WorkforceDashboardIntelOut:
        # Attendance (today)
        attendance_rows = await self.db.execute(
            select(
                WorkforceAttendanceRecord.status,
                func.count().label("count"),
                func.sum(func.cast(WorkforceAttendanceRecord.is_late, Integer)).label("late_count"),
                func.sum(func.cast(WorkforceAttendanceRecord.missing_checkout, Integer)).label("missing_checkout_count"),
            ).where(
                WorkforceAttendanceRecord.org_id == org_id,
                WorkforceAttendanceRecord.work_date == as_of,
            ).group_by(WorkforceAttendanceRecord.status)
        )

        present = 0
        absent = 0
        late = 0
        missing_checkout = 0
        for status, count, late_count, missing_checkout_count in attendance_rows.all():
            s = str(status or "").upper()
            c = int(count or 0)
            if s == "PRESENT":
                present += c
            elif s == "ABSENT":
                absent += c
            late += int(late_count or 0)
            missing_checkout += int(missing_checkout_count or 0)

        # Leave pending
        pending_leave = await self.db.scalar(
            select(func.count()).select_from(WorkforceLeaveRequest).where(
                WorkforceLeaveRequest.org_id == org_id,
                WorkforceLeaveRequest.status == "PENDING",
            )
        )

        # Payroll due soon: any period ending within 7 days that isn't PAID
        due_end = as_of + timedelta(days=7)
        payroll_due_periods = await self.db.scalar(
            select(func.count()).select_from(WorkforcePayrollPeriod).where(
                WorkforcePayrollPeriod.org_id == org_id,
                WorkforcePayrollPeriod.status != "PAID",
                WorkforcePayrollPeriod.end_date <= due_end,
            )
        )
        unpaid_entries = await self.db.scalar(
            select(func.count()).select_from(WorkforcePayrollEntry).where(
                WorkforcePayrollEntry.org_id == org_id,
                WorkforcePayrollEntry.status != "PAID",
            )
        )

        # Contract/probation tracking (30d window)
        window_end = as_of + timedelta(days=30)
        contract_expiring = await self.db.scalar(
            select(func.count()).select_from(WorkforceEmployee).where(
                WorkforceEmployee.org_id == org_id,
                WorkforceEmployee.is_active.is_(True),
                WorkforceEmployee.contract_end.is_not(None),
                WorkforceEmployee.contract_end >= as_of,
                WorkforceEmployee.contract_end <= window_end,
            )
        )
        probation_ending = await self.db.scalar(
            select(func.count()).select_from(WorkforceEmployee).where(
                WorkforceEmployee.org_id == org_id,
                WorkforceEmployee.is_active.is_(True),
                WorkforceEmployee.probation_end.is_not(None),
                WorkforceEmployee.probation_end >= as_of,
                WorkforceEmployee.probation_end <= window_end,
            )
        )

        # Unacknowledged announcements (published and acknowledgement_required)
        # Approximation: count announcements with required ack that have *zero* receipts with acknowledged_at.
        # We keep it simple/deterministic for Phase 7; deeper per-user ack coverage is Phase 8 polish.
        ann_rows = await self.db.execute(
            select(WorkforceAnnouncement.id)
            .where(
                WorkforceAnnouncement.org_id == org_id,
                WorkforceAnnouncement.status == "PUBLISHED",
                WorkforceAnnouncement.acknowledgement_required.is_(True),
                WorkforceAnnouncement.published_at.is_not(None),
                func.coalesce(WorkforceAnnouncement.expires_at, as_of) >= as_of,
            )
            .limit(500)
        )
        announcement_ids = [r[0] for r in ann_rows.all()]
        unacked_announcements = 0
        if announcement_ids:
            acked_ids = await self.db.execute(
                select(WorkforceAnnouncementReceipt.announcement_id)
                .where(
                    WorkforceAnnouncementReceipt.announcement_id.in_(announcement_ids),
                    WorkforceAnnouncementReceipt.acknowledged_at.is_not(None),
                )
                .group_by(WorkforceAnnouncementReceipt.announcement_id)
            )
            acked_set = {r[0] for r in acked_ids.all()}
            unacked_announcements = sum(1 for a_id in announcement_ids if a_id not in acked_set)

        out = WorkforceDashboardIntelOut(
            org_id=org_id,
            as_of=as_of,
            present_today=present,
            absent_today=absent,
            late_today=late,
            missing_checkout_today=missing_checkout,
            pending_leave_requests=int(pending_leave or 0),
            payroll_due_periods=int(payroll_due_periods or 0),
            unpaid_payroll_entries=int(unpaid_entries or 0),
            contract_expiring_soon=int(contract_expiring or 0),
            probation_ending_soon=int(probation_ending or 0),
            unacknowledged_announcements=int(unacked_announcements or 0),
            top_risks=[],
        )

        # Build risk strings in deterministic priority order.
        risks: list[str] = []
        if out.missing_checkout_today:
            risks.append(f"{out.missing_checkout_today} missing check-outs today")
        if out.late_today:
            risks.append(f"{out.late_today} late check-ins today")
        if out.pending_leave_requests:
            risks.append(f"{out.pending_leave_requests} pending leave requests")
        if out.payroll_due_periods:
            risks.append(f"{out.payroll_due_periods} payroll periods due within 7 days")
        if out.unpaid_payroll_entries:
            risks.append(f"{out.unpaid_payroll_entries} unpaid payroll entries")
        if out.contract_expiring_soon:
            risks.append(f"{out.contract_expiring_soon} contracts expiring within 30 days")
        if out.probation_ending_soon:
            risks.append(f"{out.probation_ending_soon} probations ending within 30 days")
        if out.unacknowledged_announcements:
            risks.append(f"{out.unacknowledged_announcements} announcements need acknowledgement")
        out.top_risks = risks[:10]
        return out

    async def reports_summary(self, *, org_id: uuid.UUID, from_date: date, to_date: date) -> WorkforceReportsSummaryOut:
        d0, d1 = from_date, to_date
        if d0 > d1:
            d0, d1 = d1, d0

        period_overlap = and_(
            WorkforcePayrollPeriod.org_id == org_id,
            WorkforcePayrollPeriod.start_date <= d1,
            WorkforcePayrollPeriod.end_date >= d0,
        )

        attendance_rows = await self.db.execute(
            select(
                WorkforceAttendanceRecord.status,
                func.count().label("count"),
                func.sum(func.cast(WorkforceAttendanceRecord.is_late, Integer)).label("late_count"),
                func.sum(func.cast(WorkforceAttendanceRecord.missing_checkout, Integer)).label("missing_checkout_count"),
            )
            .where(
                WorkforceAttendanceRecord.org_id == org_id,
                WorkforceAttendanceRecord.work_date >= d0,
                WorkforceAttendanceRecord.work_date <= d1,
            )
            .group_by(WorkforceAttendanceRecord.status)
        )

        present_days = 0
        absent_days = 0
        late_incidents = 0
        missing_checkouts = 0
        total_records = 0
        for status, count, late_count, missing_checkout_count in attendance_rows.all():
            s = str(status or "").upper()
            c = int(count or 0)
            total_records += c
            if s == "PRESENT":
                present_days += c
            elif s == "ABSENT":
                absent_days += c
            late_incidents += int(late_count or 0)
            missing_checkouts += int(missing_checkout_count or 0)

        pending_leave = await self.db.scalar(
            select(func.count()).select_from(WorkforceLeaveRequest).where(
                WorkforceLeaveRequest.org_id == org_id,
                WorkforceLeaveRequest.status == "PENDING",
            )
        )
        approved_leave_overlap = await self.db.scalar(
            select(func.count()).select_from(WorkforceLeaveRequest).where(
                WorkforceLeaveRequest.org_id == org_id,
                WorkforceLeaveRequest.status == "APPROVED",
                WorkforceLeaveRequest.start_date <= d1,
                WorkforceLeaveRequest.end_date >= d0,
            )
        )

        periods_overlapping = await self.db.scalar(
            select(func.count()).select_from(WorkforcePayrollPeriod).where(period_overlap)
        )

        total_net_raw = await self.db.scalar(
            select(func.coalesce(func.sum(WorkforcePayrollEntry.net_pay), 0))
            .select_from(WorkforcePayrollEntry)
            .join(WorkforcePayrollPeriod, WorkforcePayrollPeriod.id == WorkforcePayrollEntry.payroll_period_id)
            .where(WorkforcePayrollEntry.org_id == org_id, period_overlap)
        )
        total_net = Decimal(str(total_net_raw or 0)).quantize(Decimal("0.01"))

        unpaid_in_range = await self.db.scalar(
            select(func.count())
            .select_from(WorkforcePayrollEntry)
            .join(WorkforcePayrollPeriod, WorkforcePayrollPeriod.id == WorkforcePayrollEntry.payroll_period_id)
            .where(
                WorkforcePayrollEntry.org_id == org_id,
                period_overlap,
                WorkforcePayrollEntry.status != "PAID",
            )
        )

        dept_name = func.coalesce(WorkforceDepartment.name, "Unassigned").label("dept_name")
        hc_rows = await self.db.execute(
            select(
                WorkforceEmployee.department_id,
                dept_name,
                func.count(WorkforceEmployee.id).label("hc"),
            )
            .select_from(WorkforceEmployee)
            .outerjoin(
                WorkforceDepartment,
                WorkforceDepartment.id == WorkforceEmployee.department_id,
            )
            .where(
                WorkforceEmployee.org_id == org_id,
                WorkforceEmployee.is_active.is_(True),
            )
            .group_by(WorkforceEmployee.department_id, dept_name)
            .order_by(dept_name)
        )
        department_headcount: list[WorkforceDepartmentHeadcountOut] = []
        for dept_id, name, hc in hc_rows.all():
            department_headcount.append(
                WorkforceDepartmentHeadcountOut(
                    department_id=dept_id,
                    department_name=str(name or "Unassigned"),
                    headcount=int(hc or 0),
                )
            )

        labor_rows = await self.db.execute(
            select(
                WorkforcePayrollPeriod.id,
                WorkforcePayrollPeriod.start_date,
                WorkforcePayrollPeriod.end_date,
                func.coalesce(func.sum(WorkforcePayrollEntry.net_pay), 0).label("net"),
            )
            .select_from(WorkforcePayrollPeriod)
            .join(WorkforcePayrollEntry, WorkforcePayrollEntry.payroll_period_id == WorkforcePayrollPeriod.id)
            .where(WorkforcePayrollEntry.org_id == org_id, period_overlap)
            .group_by(
                WorkforcePayrollPeriod.id,
                WorkforcePayrollPeriod.start_date,
                WorkforcePayrollPeriod.end_date,
            )
            .order_by(WorkforcePayrollPeriod.start_date)
        )
        labor_cost_by_period: list[WorkforceLaborCostPeriodOut] = []
        for pid, pstart, pend, net_sum in labor_rows.all():
            period_net = Decimal(str(net_sum or 0)).quantize(Decimal("0.01"))
            labor_cost_by_period.append(
                WorkforceLaborCostPeriodOut(
                    payroll_period_id=pid,
                    period_start=pstart,
                    period_end=pend,
                    total_net_pay=str(period_net),
                )
            )

        summary_lines: list[str] = [
            f"Date range {d0.isoformat()} to {d1.isoformat()}: {total_records} attendance rows, "
            f"{present_days} present / {absent_days} absent person-days.",
            f"Late flags: {late_incidents}; missing check-outs: {missing_checkouts}.",
            f"Leave: {int(pending_leave or 0)} pending; {int(approved_leave_overlap or 0)} approved requests overlap the range.",
            f"Payroll: {int(periods_overlapping or 0)} periods overlap range; net pay total {total_net} "
            f"across overlapping periods; {int(unpaid_in_range or 0)} unpaid entries in those periods.",
            f"Active headcount by department: {len(department_headcount)} group(s).",
        ]

        return WorkforceReportsSummaryOut(
            org_id=org_id,
            from_date=d0,
            to_date=d1,
            attendance=WorkforceAttendanceSummaryOut(
                present_days=present_days,
                absent_days=absent_days,
                late_incidents=late_incidents,
                missing_checkouts=missing_checkouts,
                total_records=total_records,
            ),
            leave=WorkforceLeaveSummaryOut(
                pending_requests=int(pending_leave or 0),
                approved_requests_overlapping=int(approved_leave_overlap or 0),
            ),
            payroll=WorkforcePayrollSummaryOut(
                periods_overlapping=int(periods_overlapping or 0),
                total_net_pay_in_range=str(total_net),
                unpaid_entries_in_overlapping_periods=int(unpaid_in_range or 0),
            ),
            department_headcount=department_headcount,
            labor_cost_by_period=labor_cost_by_period,
            summary_lines=summary_lines,
        )

