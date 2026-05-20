from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo


@dataclass(frozen=True)
class WorkforceAccessScope:
    role: str
    actor_user_id: uuid.UUID
    actor_email: str
    manager_employee_id: uuid.UUID | None
    team_employee_ids: set[uuid.UUID]

    @property
    def is_owner(self) -> bool:
        return self.role == "OWNER"

    @property
    def is_editor(self) -> bool:
        return self.role == "EDITOR"

    @property
    def is_manager(self) -> bool:
        return self.role == "MANAGER"

    @property
    def can_edit(self) -> bool:
        return self.role in {"OWNER", "EDITOR"}

    @property
    def can_operate_team(self) -> bool:
        return self.role in {"OWNER", "EDITOR", "MANAGER"}

    def can_access_employee(self, employee_id: uuid.UUID) -> bool:
        if self.role in {"OWNER", "EDITOR", "VIEWER"}:
            return True
        if not self.is_manager:
            return False
        if self.manager_employee_id and employee_id == self.manager_employee_id:
            return True
        return employee_id in self.team_employee_ids

    def should_redact_compensation(self) -> bool:
        return self.role in {"VIEWER", "MANAGER"}


async def build_workforce_access_scope(
    *,
    db: AsyncSession,
    org_id: uuid.UUID,
    role: str,
    actor_user_id: uuid.UUID,
    actor_email: str,
) -> WorkforceAccessScope:
    repo = WorkforceEmployeeRepo(db)
    normalized_role = (role or "").strip().upper()
    manager_employee_id: uuid.UUID | None = None
    team_employee_ids: set[uuid.UUID] = set()
    if normalized_role == "MANAGER":
        actor_emp = await repo.get_by_email_ci(org_id=org_id, email=actor_email)
        if actor_emp is not None:
            manager_employee_id = actor_emp.id
            team_rows = await repo.list_by_org(
                org_id=org_id,
                include_inactive=True,
                manager_employee_id=actor_emp.id,
                limit=5000,
            )
            team_employee_ids = {row.id for row in team_rows}
    return WorkforceAccessScope(
        role=normalized_role,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        manager_employee_id=manager_employee_id,
        team_employee_ids=team_employee_ids,
    )

