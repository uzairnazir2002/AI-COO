from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_leave_request import WorkforceLeaveRequest
from app.domain.models.workforce_leave_type import WorkforceLeaveType


def overlap_inclusive_calendar_days(a_start: date, a_end: date, b_start: date, b_end: date) -> int:
    s = max(a_start, b_start)
    e = min(a_end, b_end)
    if s > e:
        return 0
    return (e - s).days + 1


class WorkforceLeaveRequestRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, *, org_id: uuid.UUID, request_id: uuid.UUID) -> WorkforceLeaveRequest | None:
        rows = await self.db.execute(
            select(WorkforceLeaveRequest).where(
                WorkforceLeaveRequest.org_id == org_id, WorkforceLeaveRequest.id == request_id
            )
        )
        return rows.scalar_one_or_none()

    async def list_by_org(
        self,
        *,
        org_id: uuid.UUID,
        status: str | None = None,
        employee_id: uuid.UUID | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 200,
    ) -> list[WorkforceLeaveRequest]:
        q = select(WorkforceLeaveRequest).where(WorkforceLeaveRequest.org_id == org_id)
        if status is not None:
            q = q.where(WorkforceLeaveRequest.status == status)
        if employee_id is not None:
            q = q.where(WorkforceLeaveRequest.employee_id == employee_id)
        if from_date is not None:
            q = q.where(WorkforceLeaveRequest.end_date >= from_date)
        if to_date is not None:
            q = q.where(WorkforceLeaveRequest.start_date <= to_date)
        q = q.order_by(WorkforceLeaveRequest.created_at.desc()).limit(max(1, min(int(limit), 500)))
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def has_overlapping_approved(
        self,
        *,
        org_id: uuid.UUID,
        employee_id: uuid.UUID,
        start_date: date,
        end_date: date,
        exclude_request_id: uuid.UUID | None = None,
    ) -> bool:
        q = select(WorkforceLeaveRequest.id).where(
            WorkforceLeaveRequest.org_id == org_id,
            WorkforceLeaveRequest.employee_id == employee_id,
            WorkforceLeaveRequest.status == "APPROVED",
            and_(WorkforceLeaveRequest.start_date <= end_date, WorkforceLeaveRequest.end_date >= start_date),
        )
        if exclude_request_id is not None:
            q = q.where(WorkforceLeaveRequest.id != exclude_request_id)
        rows = await self.db.execute(q.limit(1))
        return rows.scalar_one_or_none() is not None

    async def create(self, row: WorkforceLeaveRequest) -> WorkforceLeaveRequest:
        self.db.add(row)
        await self.db.flush()
        return row

    async def update(self, row: WorkforceLeaveRequest) -> WorkforceLeaveRequest:
        self.db.add(row)
        await self.db.flush()
        return row

    async def sum_unpaid_leave_overlap_days_in_period(
        self,
        *,
        org_id: uuid.UUID,
        employee_id: uuid.UUID,
        period_start: date,
        period_end: date,
    ) -> Decimal:
        """Approved leave requests with unpaid leave types; summed overlap days with the period (calendar days)."""
        q = (
            select(WorkforceLeaveRequest)
            .join(WorkforceLeaveType, WorkforceLeaveType.id == WorkforceLeaveRequest.leave_type_id)
            .where(
                WorkforceLeaveRequest.org_id == org_id,
                WorkforceLeaveRequest.employee_id == employee_id,
                WorkforceLeaveRequest.status == "APPROVED",
                WorkforceLeaveType.is_paid.is_(False),
                WorkforceLeaveRequest.end_date >= period_start,
                WorkforceLeaveRequest.start_date <= period_end,
            )
        )
        rows = await self.db.execute(q)
        requests = list(rows.scalars().all())
        total = 0
        for r in requests:
            total += overlap_inclusive_calendar_days(r.start_date, r.end_date, period_start, period_end)
        period_days = (period_end - period_start).days + 1
        capped = min(total, period_days)
        return Decimal(capped).quantize(Decimal("0.01"))

