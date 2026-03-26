from __future__ import annotations

import uuid

from app.domain.models.location import Location
from app.domain.repos.location_repo import LocationRepo
from app.domain.services.errors import NotFoundError


class LocationService:
    def __init__(self, repo: LocationRepo):
        self.repo = repo

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValueError("Location name is required")
        return normalized

    @staticmethod
    def _normalize_code(code: str | None) -> str | None:
        if code is None:
            return None
        normalized = code.strip().upper()
        return normalized or None

    async def list_locations(self, org_id: uuid.UUID, *, include_inactive: bool = False) -> list[Location]:
        return await self.repo.list_by_org(org_id=org_id, include_inactive=include_inactive)

    async def create_location(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        name: str,
        code: str | None,
        is_active: bool = True,
    ) -> Location:
        normalized_name = self._normalize_name(name)
        normalized_code = self._normalize_code(code)
        duplicate = await self.repo.get_by_name_or_code(
            org_id=org_id,
            name=normalized_name,
            code=normalized_code,
        )
        if duplicate:
            raise ValueError("Location name or code already exists")
        return await self.repo.create(
            Location(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                name=normalized_name,
                code=normalized_code,
                is_active=is_active,
            )
        )

    async def update_location(
        self,
        *,
        org_id: uuid.UUID,
        location_id: uuid.UUID,
        name: str | None,
        code: str | None,
        is_active: bool | None,
    ) -> Location:
        location = await self.repo.get_by_id(location_id=location_id, org_id=org_id)
        if location is None:
            raise NotFoundError("Location not found")

        if name is not None:
            location.name = self._normalize_name(name)
        if code is not None:
            location.code = self._normalize_code(code)
        if is_active is not None:
            location.is_active = is_active

        duplicate = await self.repo.get_by_name_or_code(
            org_id=org_id,
            name=location.name,
            code=location.code,
            exclude_location_id=location_id,
        )
        if duplicate:
            raise ValueError("Location name or code already exists")
        return location

    async def deactivate_location(self, *, org_id: uuid.UUID, location_id: uuid.UUID) -> Location:
        location = await self.repo.get_by_id(location_id=location_id, org_id=org_id)
        if location is None:
            raise NotFoundError("Location not found")
        location.is_active = False
        return location

    async def ensure_org_location(
        self,
        *,
        org_id: uuid.UUID,
        location_id: uuid.UUID | None,
        require_active: bool = True,
    ) -> Location | None:
        if location_id is None:
            return None
        location = await self.repo.get_by_id(location_id=location_id, org_id=org_id)
        if location is None:
            raise NotFoundError("Location not found")
        if require_active and not location.is_active:
            raise ValueError("Location is inactive")
        return location
