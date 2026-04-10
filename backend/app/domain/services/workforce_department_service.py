from __future__ import annotations

import uuid

from app.domain.models.workforce_department import WorkforceDepartment
from app.domain.repos.workforce_department_repo import WorkforceDepartmentRepo
from app.domain.services.errors import NotFoundError


class WorkforceDepartmentService:
    def __init__(self, repo: WorkforceDepartmentRepo):
        self.repo = repo

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValueError("Department name is required")
        return normalized

    @staticmethod
    def _normalize_code(code: str | None) -> str | None:
        if code is None:
            return None
        normalized = code.strip().upper()
        return normalized or None

    async def list_departments(self, *, org_id: uuid.UUID, include_inactive: bool = False) -> list[WorkforceDepartment]:
        return await self.repo.list_by_org(org_id=org_id, include_inactive=include_inactive)

    async def create_department(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        name: str,
        code: str | None,
        is_active: bool = True,
    ) -> WorkforceDepartment:
        normalized_name = self._normalize_name(name)
        normalized_code = self._normalize_code(code)
        duplicate = await self.repo.get_by_name_or_code(
            org_id=org_id,
            name=normalized_name,
            code=normalized_code,
        )
        if duplicate:
            raise ValueError("Department name or code already exists")
        return await self.repo.create(
            WorkforceDepartment(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                name=normalized_name,
                code=normalized_code,
                is_active=is_active,
            )
        )

    async def update_department(
        self,
        *,
        org_id: uuid.UUID,
        department_id: uuid.UUID,
        name: str | None,
        code: str | None,
        is_active: bool | None,
    ) -> WorkforceDepartment:
        row = await self.repo.get_by_id(org_id=org_id, department_id=department_id)
        if row is None:
            raise NotFoundError("Department not found")
        if name is not None:
            row.name = self._normalize_name(name)
        if code is not None:
            row.code = self._normalize_code(code)
        if is_active is not None:
            row.is_active = is_active

        duplicate = await self.repo.get_by_name_or_code(
            org_id=org_id,
            name=row.name,
            code=row.code,
            exclude_department_id=department_id,
        )
        if duplicate:
            raise ValueError("Department name or code already exists")
        return row

    async def deactivate_department(self, *, org_id: uuid.UUID, department_id: uuid.UUID) -> WorkforceDepartment:
        row = await self.repo.get_by_id(org_id=org_id, department_id=department_id)
        if row is None:
            raise NotFoundError("Department not found")
        row.is_active = False
        return row

