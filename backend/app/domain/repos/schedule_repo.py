from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.schedule_control import ScheduleControl
from app.utils.time import utc_now


class ScheduleRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, name: str) -> ScheduleControl | None:
        return await self.db.scalar(select(ScheduleControl).where(ScheduleControl.name == name))

    async def list_all(self) -> list[ScheduleControl]:
        return list((await self.db.execute(select(ScheduleControl))).scalars().all())

    async def set_paused(self, name: str, paused: bool) -> ScheduleControl:
        row = await self.get(name)
        if not row:
            row = ScheduleControl(name=name, paused=paused)
            self.db.add(row)
        else:
            row.paused = paused
            row.updated_at = utc_now()
        await self.db.flush()
        return row
