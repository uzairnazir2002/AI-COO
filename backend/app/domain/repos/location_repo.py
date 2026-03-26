from __future__ import annotations

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.location import Location


class LocationRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_org(self, org_id: uuid.UUID, *, include_inactive: bool = False) -> list[Location]:
        query = select(Location).where(Location.org_id == org_id)
        if not include_inactive:
            query = query.where(Location.is_active.is_(True))
        query = query.order_by(Location.name.asc())
        rows = await self.db.execute(query)
        return list(rows.scalars().all())

    async def get_by_id(self, location_id: uuid.UUID, org_id: uuid.UUID) -> Location | None:
        row = await self.db.execute(
            select(Location).where(Location.id == location_id, Location.org_id == org_id)
        )
        return row.scalar_one_or_none()

    async def get_by_name_or_code(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        code: str | None,
        exclude_location_id: uuid.UUID | None = None,
    ) -> Location | None:
        filters = [Location.org_id == org_id, or_(Location.name == name, Location.code == code)]
        if code is None:
            filters = [Location.org_id == org_id, Location.name == name]
        if exclude_location_id:
            filters.append(Location.id != exclude_location_id)
        row = await self.db.execute(select(Location).where(and_(*filters)))
        return row.scalar_one_or_none()

    async def create(self, location: Location) -> Location:
        self.db.add(location)
        await self.db.flush()
        return location
