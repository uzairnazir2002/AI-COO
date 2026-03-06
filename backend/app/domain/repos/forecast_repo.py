import uuid
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.forecast import Forecast


class ForecastRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_forecasts(self, org_id: uuid.UUID, months: int) -> list[Forecast]:
        q = await self.db.execute(
            select(Forecast).where(Forecast.org_id == org_id).order_by(Forecast.month.asc()).limit(months * 3)
        )
        return list(q.scalars().all())

    async def get_one(self, org_id: uuid.UUID, month: date, scenario: str) -> Forecast | None:
        q = await self.db.execute(
            select(Forecast).where(Forecast.org_id == org_id, Forecast.month == month, Forecast.scenario == scenario)
        )
        return q.scalar_one_or_none()

    async def save(self, forecast: Forecast) -> Forecast:
        self.db.add(forecast)
        await self.db.flush()
        return forecast

    async def delete_for_org(self, org_id: uuid.UUID) -> int:
        result = await self.db.execute(delete(Forecast).where(Forecast.org_id == org_id))
        return int(result.rowcount or 0)
