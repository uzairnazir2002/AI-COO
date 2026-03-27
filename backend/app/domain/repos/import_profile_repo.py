import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.import_mapping_profile import ImportMappingProfile


class ImportProfileRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_visible(self, org_id: uuid.UUID, user_id: uuid.UUID) -> list[ImportMappingProfile]:
        q = await self.db.execute(
            select(ImportMappingProfile)
            .where(
                ImportMappingProfile.org_id == org_id,
                (ImportMappingProfile.user_id.is_(None)) | (ImportMappingProfile.user_id == user_id),
            )
            .order_by(ImportMappingProfile.updated_at.desc())
        )
        return list(q.scalars().all())

    async def get(self, profile_id: uuid.UUID, org_id: uuid.UUID) -> ImportMappingProfile | None:
        q = await self.db.execute(
            select(ImportMappingProfile).where(
                ImportMappingProfile.id == profile_id,
                ImportMappingProfile.org_id == org_id,
            )
        )
        return q.scalar_one_or_none()

    async def create(self, profile: ImportMappingProfile) -> ImportMappingProfile:
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def save(self, profile: ImportMappingProfile) -> ImportMappingProfile:
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def delete(self, profile: ImportMappingProfile) -> None:
        await self.db.delete(profile)
        await self.db.flush()
