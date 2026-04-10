from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Integer, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_attendance_correction import WorkforceAttendanceCorrection
from app.domain.models.workforce_attendance_record import WorkforceAttendanceRecord


class WorkforceAttendanceRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_record_for_date(
        self, *, org_id: uuid.UUID, employee_id: uuid.UUID, work_date: date
    ) -> WorkforceAttendanceRecord | None:
        row = await self.db.execute(
            select(WorkforceAttendanceRecord).where(
                WorkforceAttendanceRecord.org_id == org_id,
                WorkforceAttendanceRecord.employee_id == employee_id,
                WorkforceAttendanceRecord.work_date == work_date,
            )
        )
        return row.scalar_one_or_none()

    async def get_record(self, *, org_id: uuid.UUID, record_id: uuid.UUID) -> WorkforceAttendanceRecord | None:
        row = await self.db.execute(
            select(WorkforceAttendanceRecord).where(
                WorkforceAttendanceRecord.org_id == org_id, WorkforceAttendanceRecord.id == record_id
            )
        )
        return row.scalar_one_or_none()

    async def upsert_record(self, row: WorkforceAttendanceRecord) -> WorkforceAttendanceRecord:
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_records(
        self,
        *,
        org_id: uuid.UUID,
        from_date: date,
        to_date: date,
        employee_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 1000,
    ) -> list[WorkforceAttendanceRecord]:
        q = select(WorkforceAttendanceRecord).where(
            WorkforceAttendanceRecord.org_id == org_id,
            WorkforceAttendanceRecord.work_date >= from_date,
            WorkforceAttendanceRecord.work_date <= to_date,
        )
        if employee_id is not None:
            q = q.where(WorkforceAttendanceRecord.employee_id == employee_id)
        if status is not None:
            q = q.where(WorkforceAttendanceRecord.status == status)
        q = q.order_by(WorkforceAttendanceRecord.work_date.asc(), WorkforceAttendanceRecord.employee_id.asc())
        q = q.limit(max(1, min(int(limit), 5000)))
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def calendar_counts(
        self,
        *,
        org_id: uuid.UUID,
        from_date: date,
        to_date: date,
    ) -> list[dict]:
        q = (
            select(
                WorkforceAttendanceRecord.work_date.label("day"),
                WorkforceAttendanceRecord.status.label("status"),
                func.count().label("count"),
                func.sum(func.cast(WorkforceAttendanceRecord.is_late, Integer)).label("late_count"),
                func.sum(func.cast(WorkforceAttendanceRecord.missing_checkout, Integer)).label(
                    "missing_checkout_count"
                ),
            )
            .where(
                WorkforceAttendanceRecord.org_id == org_id,
                WorkforceAttendanceRecord.work_date >= from_date,
                WorkforceAttendanceRecord.work_date <= to_date,
            )
            .group_by(WorkforceAttendanceRecord.work_date, WorkforceAttendanceRecord.status)
            .order_by(WorkforceAttendanceRecord.work_date.asc())
        )
        rows = await self.db.execute(q)
        result = []
        for day, status, count, late_count, missing_checkout_count in rows.all():
            result.append(
                {
                    "day": day,
                    "status": status,
                    "count": int(count),
                    "late_count": int(late_count or 0),
                    "missing_checkout_count": int(missing_checkout_count or 0),
                }
            )
        return result

    async def create_correction(self, row: WorkforceAttendanceCorrection) -> WorkforceAttendanceCorrection:
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_correction(self, *, org_id: uuid.UUID, correction_id: uuid.UUID) -> WorkforceAttendanceCorrection | None:
        row = await self.db.execute(
            select(WorkforceAttendanceCorrection).where(
                WorkforceAttendanceCorrection.org_id == org_id, WorkforceAttendanceCorrection.id == correction_id
            )
        )
        return row.scalar_one_or_none()

    async def list_corrections(
        self,
        *,
        org_id: uuid.UUID,
        status: str | None = None,
        employee_id: uuid.UUID | None = None,
        limit: int = 200,
    ) -> list[WorkforceAttendanceCorrection]:
        q = select(WorkforceAttendanceCorrection).where(WorkforceAttendanceCorrection.org_id == org_id)
        if status is not None:
            q = q.where(WorkforceAttendanceCorrection.status == status)
        if employee_id is not None:
            q = q.where(WorkforceAttendanceCorrection.employee_id == employee_id)
        q = q.order_by(WorkforceAttendanceCorrection.created_at.desc()).limit(max(1, min(int(limit), 500)))
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

