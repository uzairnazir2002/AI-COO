import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.alert import Alert


class AlertRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_alerts(self, org_id: uuid.UUID, status: str | None) -> list[Alert]:
        q = select(Alert).where(Alert.org_id == org_id).order_by(Alert.created_at.desc())
        if status:
            q = q.where(Alert.status == status.upper())
        res = await self.db.execute(q)
        return list(res.scalars().all())

    async def get(self, alert_id: uuid.UUID, org_id: uuid.UUID) -> Alert | None:
        res = await self.db.execute(select(Alert).where(Alert.id == alert_id, Alert.org_id == org_id))
        return res.scalar_one_or_none()

    async def save(self, alert: Alert) -> Alert:
        self.db.add(alert)
        await self.db.flush()
        return alert

    async def clear_open(self, org_id: uuid.UUID) -> int:
        result = await self.db.execute(delete(Alert).where(Alert.org_id == org_id, Alert.status == "OPEN"))
        return int(result.rowcount or 0)
