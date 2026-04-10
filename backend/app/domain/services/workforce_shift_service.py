from __future__ import annotations

import uuid
from datetime import date, time

from app.domain.models.workforce_shift import WorkforceShift
from app.domain.models.workforce_shift_assignment import WorkforceShiftAssignment
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_shift_repo import WorkforceShiftRepo
from app.domain.services.errors import NotFoundError


class WorkforceShiftService:
    def __init__(self, *, shift_repo: WorkforceShiftRepo, employee_repo: WorkforceEmployeeRepo):
        self.shift_repo = shift_repo
        self.employee_repo = employee_repo

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValueError("Shift name is required")
        return normalized

    @staticmethod
    def _validate_times(start_time: time, end_time: time) -> None:
        if start_time == end_time:
            raise ValueError("Shift start_time and end_time cannot be the same")

    async def list_shifts(self, *, org_id: uuid.UUID, include_inactive: bool = False) -> list[WorkforceShift]:
        return await self.shift_repo.list_shifts(org_id=org_id, include_inactive=include_inactive)

    async def create_shift(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        name: str,
        start_time: time,
        end_time: time,
        grace_minutes: int,
        is_active: bool = True,
    ) -> WorkforceShift:
        normalized_name = self._normalize_name(name)
        self._validate_times(start_time, end_time)
        existing = await self.shift_repo.get_shift_by_name(org_id=org_id, name=normalized_name)
        if existing:
            raise ValueError("Shift already exists")
        return await self.shift_repo.create_shift(
            WorkforceShift(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                name=normalized_name,
                start_time=start_time,
                end_time=end_time,
                grace_minutes=grace_minutes,
                is_active=is_active,
            )
        )

    async def update_shift(
        self,
        *,
        org_id: uuid.UUID,
        shift_id: uuid.UUID,
        name: str | None,
        start_time: time | None,
        end_time: time | None,
        grace_minutes: int | None,
        is_active: bool | None,
    ) -> WorkforceShift:
        row = await self.shift_repo.get_shift(org_id=org_id, shift_id=shift_id)
        if row is None:
            raise NotFoundError("Shift not found")
        if name is not None:
            row.name = self._normalize_name(name)
        if start_time is not None:
            row.start_time = start_time
        if end_time is not None:
            row.end_time = end_time
        self._validate_times(row.start_time, row.end_time)
        if grace_minutes is not None:
            if grace_minutes < 0 or grace_minutes > 240:
                raise ValueError("grace_minutes must be between 0 and 240")
            row.grace_minutes = grace_minutes
        if is_active is not None:
            row.is_active = is_active
        dup = await self.shift_repo.get_shift_by_name(org_id=org_id, name=row.name, exclude_shift_id=shift_id)
        if dup:
            raise ValueError("Shift already exists")
        return row

    async def deactivate_shift(self, *, org_id: uuid.UUID, shift_id: uuid.UUID) -> WorkforceShift:
        row = await self.shift_repo.get_shift(org_id=org_id, shift_id=shift_id)
        if row is None:
            raise NotFoundError("Shift not found")
        row.is_active = False
        return row

    async def list_assignments(
        self,
        *,
        org_id: uuid.UUID,
        employee_id: uuid.UUID | None = None,
        shift_id: uuid.UUID | None = None,
        as_of: date | None = None,
        limit: int = 200,
    ) -> list[WorkforceShiftAssignment]:
        return await self.shift_repo.list_assignments(
            org_id=org_id, employee_id=employee_id, shift_id=shift_id, as_of=as_of, limit=limit
        )

    async def assign_shift(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        employee_id: uuid.UUID,
        shift_id: uuid.UUID,
        effective_from: date,
        effective_to: date | None,
    ) -> WorkforceShiftAssignment:
        emp = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
        if emp is None or not emp.is_active:
            raise ValueError("Employee not found")
        shift = await self.shift_repo.get_shift(org_id=org_id, shift_id=shift_id)
        if shift is None or not shift.is_active:
            raise ValueError("Shift not found")
        if effective_to is not None and effective_to < effective_from:
            raise ValueError("effective_to cannot be before effective_from")
        return await self.shift_repo.create_assignment(
            WorkforceShiftAssignment(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                employee_id=employee_id,
                shift_id=shift_id,
                effective_from=effective_from,
                effective_to=effective_to,
            )
        )

