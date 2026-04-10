from __future__ import annotations

import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_employee import WorkforceEmployee


class WorkforceEmployeeRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_org(
        self,
        *,
        org_id: uuid.UUID,
        include_inactive: bool = False,
        q: str | None = None,
        department_id: uuid.UUID | None = None,
        title_id: uuid.UUID | None = None,
        manager_employee_id: uuid.UUID | None = None,
        employment_status: str | None = None,
        limit: int = 200,
    ) -> list[WorkforceEmployee]:
        query = select(WorkforceEmployee).where(WorkforceEmployee.org_id == org_id)
        if not include_inactive:
            query = query.where(WorkforceEmployee.is_active.is_(True))
        if department_id is not None:
            query = query.where(WorkforceEmployee.department_id == department_id)
        if title_id is not None:
            query = query.where(WorkforceEmployee.title_id == title_id)
        if manager_employee_id is not None:
            query = query.where(WorkforceEmployee.manager_employee_id == manager_employee_id)
        if employment_status is not None:
            query = query.where(WorkforceEmployee.employment_status == employment_status)
        if q:
            needle = f"%{q.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(WorkforceEmployee.first_name).like(needle),
                    func.lower(WorkforceEmployee.last_name).like(needle),
                    func.lower(func.coalesce(WorkforceEmployee.email, "")).like(needle),
                    func.lower(func.coalesce(WorkforceEmployee.employee_code, "")).like(needle),
                )
            )
        query = query.order_by(WorkforceEmployee.last_name.asc(), WorkforceEmployee.first_name.asc())
        query = query.limit(max(1, min(int(limit), 500)))
        rows = await self.db.execute(query)
        return list(rows.scalars().all())

    async def get_by_id(self, *, org_id: uuid.UUID, employee_id: uuid.UUID) -> WorkforceEmployee | None:
        row = await self.db.execute(
            select(WorkforceEmployee).where(WorkforceEmployee.org_id == org_id, WorkforceEmployee.id == employee_id)
        )
        return row.scalar_one_or_none()

    async def get_by_employee_code(
        self,
        *,
        org_id: uuid.UUID,
        employee_code: str,
        exclude_employee_id: uuid.UUID | None = None,
    ) -> WorkforceEmployee | None:
        filters = [WorkforceEmployee.org_id == org_id, WorkforceEmployee.employee_code == employee_code]
        if exclude_employee_id:
            filters.append(WorkforceEmployee.id != exclude_employee_id)
        row = await self.db.execute(select(WorkforceEmployee).where(and_(*filters)))
        return row.scalar_one_or_none()

    async def create(self, row: WorkforceEmployee) -> WorkforceEmployee:
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_by_email_ci(self, *, org_id: uuid.UUID, email: str) -> WorkforceEmployee | None:
        needle = (email or "").strip().lower()
        if not needle:
            return None
        row = await self.db.execute(
            select(WorkforceEmployee).where(
                WorkforceEmployee.org_id == org_id,
                func.lower(func.coalesce(WorkforceEmployee.email, "")) == needle,
            )
        )
        return row.scalar_one_or_none()

    async def list_active_for_audience(
        self,
        *,
        org_id: uuid.UUID,
        audience_kind: str,
        audience_ids: list[uuid.UUID],
    ) -> list[WorkforceEmployee]:
        if not audience_ids:
            return []
        kind = (audience_kind or "").strip().upper()
        q = select(WorkforceEmployee).where(
            WorkforceEmployee.org_id == org_id,
            WorkforceEmployee.is_active.is_(True),
        )
        if kind == "DEPARTMENT":
            q = q.where(WorkforceEmployee.department_id.in_(audience_ids))
        elif kind == "LOCATION":
            q = q.where(WorkforceEmployee.location_id.in_(audience_ids))
        elif kind == "TITLE":
            q = q.where(WorkforceEmployee.title_id.in_(audience_ids))
        elif kind == "MANAGER_TEAM":
            q = q.where(WorkforceEmployee.manager_employee_id.in_(audience_ids))
        else:
            return []
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

