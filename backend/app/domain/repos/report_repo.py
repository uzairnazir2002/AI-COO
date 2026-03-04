import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.report import Report


class ReportRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_reports(self, org_id: uuid.UUID) -> list[Report]:
        q = await self.db.execute(
            select(Report).where(Report.org_id == org_id).order_by(Report.week_start.desc())
        )
        return list(q.scalars().all())

    async def get(self, report_id: uuid.UUID, org_id: uuid.UUID) -> Report | None:
        q = await self.db.execute(select(Report).where(Report.id == report_id, Report.org_id == org_id))
        return q.scalar_one_or_none()

    async def get_by_week(self, org_id: uuid.UUID, week_start: date) -> Report | None:
        q = await self.db.execute(
            select(Report).where(Report.org_id == org_id, Report.week_start == week_start)
        )
        return q.scalar_one_or_none()

    async def save(self, report: Report) -> Report:
        self.db.add(report)
        await self.db.flush()
        return report
