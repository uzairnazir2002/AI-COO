import uuid

from app.domain.models.import_mapping_profile import ImportMappingProfile
from app.domain.repos.import_profile_repo import ImportProfileRepo
from app.domain.services.errors import ForbiddenError, NotFoundError


class ImportProfileService:
    def __init__(self, repo: ImportProfileRepo):
        self.repo = repo

    async def list_profiles(self, org_id: uuid.UUID, user_id: uuid.UUID) -> list[ImportMappingProfile]:
        return await self.repo.list_visible(org_id, user_id)

    async def create_profile(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        name: str,
        column_map: dict,
        shared: bool,
    ) -> ImportMappingProfile:
        profile = ImportMappingProfile(
            org_id=org_id,
            user_id=None if shared else actor_user_id,
            name=name.strip(),
            column_map=column_map,
        )
        return await self.repo.create(profile)

    async def update_profile(
        self,
        *,
        profile_id: uuid.UUID,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        name: str | None,
        column_map: dict | None,
        shared: bool | None,
    ) -> ImportMappingProfile:
        profile = await self.repo.get(profile_id, org_id)
        if not profile:
            raise NotFoundError("Import mapping profile not found")
        self._assert_editable(profile, actor_user_id)
        if name is not None:
            profile.name = name.strip()
        if column_map is not None:
            profile.column_map = column_map
        if shared is not None:
            profile.user_id = None if shared else actor_user_id
        return await self.repo.save(profile)

    async def delete_profile(self, *, profile_id: uuid.UUID, org_id: uuid.UUID, actor_user_id: uuid.UUID) -> None:
        profile = await self.repo.get(profile_id, org_id)
        if not profile:
            raise NotFoundError("Import mapping profile not found")
        self._assert_editable(profile, actor_user_id)
        await self.repo.delete(profile)

    async def resolve_import_mapping(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        mapping: dict | None,
        profile_id: uuid.UUID | None,
    ) -> tuple[dict, uuid.UUID | None]:
        if mapping:
            return mapping, profile_id
        if not profile_id:
            raise ValueError("Provide mapping JSON or profile_id")
        profile = await self.repo.get(profile_id, org_id)
        if not profile:
            raise NotFoundError("Mapping profile not found")
        if profile.user_id is not None and profile.user_id != actor_user_id:
            raise ForbiddenError("Forbidden")
        return profile.column_map, profile.id

    @staticmethod
    def _assert_editable(profile: ImportMappingProfile, actor_user_id: uuid.UUID) -> None:
        if profile.user_id is not None and profile.user_id != actor_user_id:
            raise ForbiddenError("Forbidden")
