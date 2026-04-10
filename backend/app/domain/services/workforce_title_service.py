from __future__ import annotations

import uuid

from app.domain.models.workforce_title import WorkforceTitle
from app.domain.repos.workforce_title_repo import WorkforceTitleRepo
from app.domain.services.errors import NotFoundError


class WorkforceTitleService:
    def __init__(self, repo: WorkforceTitleRepo):
        self.repo = repo

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValueError("Title name is required")
        return normalized

    async def list_titles(self, *, org_id: uuid.UUID, include_inactive: bool = False) -> list[WorkforceTitle]:
        return await self.repo.list_by_org(org_id=org_id, include_inactive=include_inactive)

    async def create_title(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        name: str,
        level: int | None,
        is_active: bool = True,
    ) -> WorkforceTitle:
        normalized_name = self._normalize_name(name)
        existing = await self.repo.get_by_name(org_id=org_id, name=normalized_name)
        if existing:
            raise ValueError("Title already exists")
        return await self.repo.create(
            WorkforceTitle(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                name=normalized_name,
                level=level,
                is_active=is_active,
            )
        )

    async def update_title(
        self,
        *,
        org_id: uuid.UUID,
        title_id: uuid.UUID,
        name: str | None,
        level: int | None,
        is_active: bool | None,
    ) -> WorkforceTitle:
        row = await self.repo.get_by_id(org_id=org_id, title_id=title_id)
        if row is None:
            raise NotFoundError("Title not found")
        if name is not None:
            row.name = self._normalize_name(name)
        if level is not None:
            row.level = level
        if is_active is not None:
            row.is_active = is_active
        duplicate = await self.repo.get_by_name(org_id=org_id, name=row.name, exclude_title_id=title_id)
        if duplicate:
            raise ValueError("Title already exists")
        return row

    async def deactivate_title(self, *, org_id: uuid.UUID, title_id: uuid.UUID) -> WorkforceTitle:
        row = await self.repo.get_by_id(org_id=org_id, title_id=title_id)
        if row is None:
            raise NotFoundError("Title not found")
        row.is_active = False
        return row

