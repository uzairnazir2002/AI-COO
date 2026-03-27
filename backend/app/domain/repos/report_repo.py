import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.report import Report


class ReportRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_reports(self, org_id: uuid.UUID, *, location_id: uuid.UUID | None = None) -> list[Report]:
        query = select(Report).where(Report.org_id == org_id)
        if location_id is not None:
            query = query.where(Report.location_id == location_id)
        q = await self.db.execute(query.order_by(Report.week_start.desc()))
        return list(q.scalars().all())

    async def get(self, report_id: uuid.UUID, org_id: uuid.UUID, *, location_id: uuid.UUID | None = None) -> Report | None:
        query = select(Report).where(Report.id == report_id, Report.org_id == org_id)
        if location_id is not None:
            query = query.where(Report.location_id == location_id)
        q = await self.db.execute(query)
        return q.scalar_one_or_none()

    async def get_by_week(
        self,
        org_id: uuid.UUID,
        week_start: date,
        *,
        location_id: uuid.UUID | None = None,
    ) -> Report | None:
        query = select(Report).where(Report.org_id == org_id, Report.week_start == week_start)
        if location_id is None:
            query = query.where(Report.location_id.is_(None))
        else:
            query = query.where(Report.location_id == location_id)
        q = await self.db.execute(query)
        return q.scalar_one_or_none()

    async def save(self, report: Report) -> Report:
        self.db.add(report)
        await self.db.flush()
        return report
