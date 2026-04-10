from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.domain.models.workforce_leave_balance import WorkforceLeaveBalance
from app.domain.models.workforce_leave_request import WorkforceLeaveRequest
from app.domain.models.workforce_leave_type import WorkforceLeaveType
from app.domain.repos.workforce_attendance_repo import WorkforceAttendanceRepo
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_leave_balance_repo import WorkforceLeaveBalanceRepo
from app.domain.repos.workforce_leave_request_repo import WorkforceLeaveRequestRepo
from app.domain.repos.workforce_leave_type_repo import WorkforceLeaveTypeRepo
from app.domain.services.errors import NotFoundError
from app.domain.services.workforce_announcement_automation import (
    AUTOMATION_KEY_LEAVE_REQUEST_APPROVED,
    AUTOMATION_KEY_LEAVE_REQUEST_REJECTED,
    try_emit_automation_announcement,
)


def _norm_code(code: str | None) -> str | None:
    if code is None:
        return None
    c = code.strip()
    return c.upper() if c else None


class WorkforceLeaveService:
    def __init__(
        self,
        *,
        leave_type_repo: WorkforceLeaveTypeRepo,
        leave_balance_repo: WorkforceLeaveBalanceRepo,
        leave_request_repo: WorkforceLeaveRequestRepo,
        employee_repo: WorkforceEmployeeRepo,
        attendance_repo: WorkforceAttendanceRepo,
    ):
        self.leave_type_repo = leave_type_repo
        self.leave_balance_repo = leave_balance_repo
        self.leave_request_repo = leave_request_repo
        self.employee_repo = employee_repo
        self.attendance_repo = attendance_repo

    # Leave types
    async def list_leave_types(self, *, org_id: uuid.UUID, include_inactive: bool) -> list[WorkforceLeaveType]:
        return await self.leave_type_repo.list_by_org(org_id=org_id, include_inactive=include_inactive)

    async def create_leave_type(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        name: str,
        code: str | None,
        is_paid: bool,
        requires_approval: bool,
        is_active: bool,
    ) -> WorkforceLeaveType:
        n = name.strip()
        if not n:
            raise ValueError("Name is required")
        c = _norm_code(code)
        existing = await self.leave_type_repo.get_by_name_or_code(org_id=org_id, name=n, code=c)
        if existing is not None:
            raise ValueError("Leave type with same name/code already exists")
        row = WorkforceLeaveType(
            org_id=org_id,
            created_by_user_id=actor_user_id,
            name=n,
            code=c,
            is_paid=bool(is_paid),
            requires_approval=bool(requires_approval),
            is_active=bool(is_active),
        )
        return await self.leave_type_repo.create(row)

    async def update_leave_type(
        self,
        *,
        org_id: uuid.UUID,
        leave_type_id: uuid.UUID,
        name: str | None,
        code: str | None,
        is_paid: bool | None,
        requires_approval: bool | None,
        is_active: bool | None,
    ) -> WorkforceLeaveType:
        row = await self.leave_type_repo.get_by_id(org_id=org_id, leave_type_id=leave_type_id)
        if row is None:
            raise NotFoundError("Leave type not found")
        if name is not None:
            n = name.strip()
            if not n:
                raise ValueError("Name is required")
            row.name = n
        if code is not None:
            row.code = _norm_code(code)
        if is_paid is not None:
            row.is_paid = bool(is_paid)
        if requires_approval is not None:
            row.requires_approval = bool(requires_approval)
        if is_active is not None:
            row.is_active = bool(is_active)
        return await self.leave_type_repo.update(row)

    async def deactivate_leave_type(self, *, org_id: uuid.UUID, leave_type_id: uuid.UUID) -> WorkforceLeaveType:
        row = await self.leave_type_repo.get_by_id(org_id=org_id, leave_type_id=leave_type_id)
        if row is None:
            raise NotFoundError("Leave type not found")
        row.is_active = False
        return await self.leave_type_repo.update(row)

    # Balances
    async def list_balances(
        self,
        *,
        org_id: uuid.UUID,
        employee_id: uuid.UUID | None,
        year: int | None,
        limit: int = 2000,
    ) -> list[WorkforceLeaveBalance]:
        return await self.leave_balance_repo.list_by_org(org_id=org_id, employee_id=employee_id, year=year, limit=limit)

    async def allocate_balance(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        employee_id: uuid.UUID,
        leave_type_id: uuid.UUID,
        year: int,
        allocated_days: Decimal,
    ) -> WorkforceLeaveBalance:
        emp = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
        if emp is None or not emp.is_active:
            raise ValueError("Employee not found")
        lt = await self.leave_type_repo.get_by_id(org_id=org_id, leave_type_id=leave_type_id)
        if lt is None or not lt.is_active:
            raise ValueError("Leave type not found")
        y = int(year)
        if y < 2000 or y > 2100:
            raise ValueError("Invalid year")
        alloc = Decimal(allocated_days)
        if alloc < 0:
            raise ValueError("allocated_days must be >= 0")
        bal = await self.leave_balance_repo.get_balance(org_id=org_id, employee_id=employee_id, leave_type_id=leave_type_id, year=y)
        if bal is None:
            bal = WorkforceLeaveBalance(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                employee_id=employee_id,
                leave_type_id=leave_type_id,
                year=y,
                allocated_days=alloc,
                used_days=Decimal("0"),
                pending_days=Decimal("0"),
            )
        else:
            bal.allocated_days = alloc
        return await self.leave_balance_repo.upsert(bal)

    # Requests
    async def list_requests(
        self,
        *,
        org_id: uuid.UUID,
        status: str | None,
        employee_id: uuid.UUID | None,
        from_date: date | None,
        to_date: date | None,
        limit: int,
    ) -> list[WorkforceLeaveRequest]:
        return await self.leave_request_repo.list_by_org(
            org_id=org_id, status=status, employee_id=employee_id, from_date=from_date, to_date=to_date, limit=limit
        )

    async def create_request(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        employee_id: uuid.UUID,
        leave_type_id: uuid.UUID,
        start_date: date,
        end_date: date,
        days: Decimal,
        reason: str | None,
    ) -> WorkforceLeaveRequest:
        emp = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
        if emp is None or not emp.is_active:
            raise ValueError("Employee not found")
        lt = await self.leave_type_repo.get_by_id(org_id=org_id, leave_type_id=leave_type_id)
        if lt is None or not lt.is_active:
            raise ValueError("Leave type not found")
        if end_date < start_date:
            raise ValueError("end_date cannot be before start_date")
        if start_date.year != end_date.year:
            raise ValueError("Leave request must be within a single year")
        d = Decimal(days)
        if d <= 0:
            raise ValueError("days must be > 0")
        if await self.leave_request_repo.has_overlapping_approved(
            org_id=org_id, employee_id=employee_id, start_date=start_date, end_date=end_date
        ):
            raise ValueError("Employee already has approved leave overlapping these dates")
        normalized_reason = reason.strip() if isinstance(reason, str) and reason.strip() else None

        # balance reservation (pending)
        year = int(start_date.year)
        bal = await self.leave_balance_repo.get_balance(org_id=org_id, employee_id=employee_id, leave_type_id=leave_type_id, year=year)
        if bal is None:
            bal = WorkforceLeaveBalance(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                employee_id=employee_id,
                leave_type_id=leave_type_id,
                year=year,
                allocated_days=Decimal("0"),
                used_days=Decimal("0"),
                pending_days=Decimal("0"),
            )
        available = (bal.allocated_days or Decimal("0")) - (bal.used_days or Decimal("0")) - (bal.pending_days or Decimal("0"))
        if available < d:
            raise ValueError("Insufficient leave balance")
        bal.pending_days = (bal.pending_days or Decimal("0")) + d
        await self.leave_balance_repo.upsert(bal)

        row = WorkforceLeaveRequest(
            org_id=org_id,
            created_by_user_id=actor_user_id,
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            days=d,
            status="PENDING" if lt.requires_approval else "APPROVED",
            reason=normalized_reason,
        )
        row = await self.leave_request_repo.create(row)

        if row.status == "APPROVED":
            # auto-approve path (no approval required): consume pending->used and update attendance
            await self._apply_decision(org_id=org_id, actor_user_id=actor_user_id, request=row, decision="APPROVED", note="Auto-approved")

        return row

    async def decide_request(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        request_id: uuid.UUID,
        status: str,
        reviewer_note: str | None,
    ) -> WorkforceLeaveRequest:
        row = await self.leave_request_repo.get_by_id(org_id=org_id, request_id=request_id)
        if row is None:
            raise NotFoundError("Leave request not found")
        decision = status.strip().upper()
        if decision not in {"APPROVED", "REJECTED", "CANCELLED"}:
            raise ValueError("status must be APPROVED, REJECTED, or CANCELLED")
        if row.status not in {"PENDING"} and not (decision == "CANCELLED" and row.status == "APPROVED"):
            raise ValueError("Leave request cannot be updated from its current status")

        note = reviewer_note.strip() if isinstance(reviewer_note, str) and reviewer_note.strip() else None
        await self._apply_decision(org_id=org_id, actor_user_id=actor_user_id, request=row, decision=decision, note=note)
        return row

    async def _apply_decision(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        request: WorkforceLeaveRequest,
        decision: str,
        note: str | None,
    ) -> None:
        was_pending = request.status == "PENDING"
        year = int(request.start_date.year)
        bal = await self.leave_balance_repo.get_balance(
            org_id=org_id, employee_id=request.employee_id, leave_type_id=request.leave_type_id, year=year
        )
        if bal is None:
            bal = WorkforceLeaveBalance(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                employee_id=request.employee_id,
                leave_type_id=request.leave_type_id,
                year=year,
                allocated_days=Decimal("0"),
                used_days=Decimal("0"),
                pending_days=Decimal("0"),
            )
        days = request.days or Decimal("0")

        if decision in {"REJECTED"} and request.status == "PENDING":
            bal.pending_days = max(Decimal("0"), (bal.pending_days or Decimal("0")) - days)
        if decision == "APPROVED" and request.status == "PENDING":
            bal.pending_days = max(Decimal("0"), (bal.pending_days or Decimal("0")) - days)
            bal.used_days = (bal.used_days or Decimal("0")) + days
        if decision == "CANCELLED" and request.status == "APPROVED":
            # rollback used days (simple policy; later can enforce "cannot cancel past dates")
            bal.used_days = max(Decimal("0"), (bal.used_days or Decimal("0")) - days)
        await self.leave_balance_repo.upsert(bal)

        request.status = decision
        request.reviewed_by_user_id = actor_user_id
        request.reviewed_at = datetime.now(tz=timezone.utc)
        request.reviewer_note = note
        await self.leave_request_repo.update(request)

        # Attendance interaction (Phase 3 requirement): mark leave days as LEAVE on approval.
        if decision == "APPROVED":
            cursor = request.start_date
            while cursor <= request.end_date:
                row = await self.attendance_repo.get_record_for_date(org_id=org_id, employee_id=request.employee_id, work_date=cursor)
                if row is None:
                    from app.domain.models.workforce_attendance_record import WorkforceAttendanceRecord

                    row = WorkforceAttendanceRecord(
                        org_id=org_id,
                        employee_id=request.employee_id,
                        created_by_user_id=actor_user_id,
                        work_date=cursor,
                        status="LEAVE",
                        source="MANUAL",
                        notes=f"Leave {request.id}",
                    )
                else:
                    row.status = "LEAVE"
                    row.source = "MANUAL"
                    row.clock_in_at = None
                    row.clock_out_at = None
                    row.worked_minutes = 0
                    row.overtime_minutes = 0
                    row.payable_hours = Decimal("0")
                    row.notes = f"Leave {request.id}"
                await self.attendance_repo.upsert_record(row)
                cursor = cursor + timedelta(days=1)

        # If an approved leave is cancelled, revert only rows that were clearly created/overwritten by this leave.
        if decision == "CANCELLED":
            cursor = request.start_date
            expected_note = f"Leave {request.id}"
            while cursor <= request.end_date:
                row = await self.attendance_repo.get_record_for_date(
                    org_id=org_id, employee_id=request.employee_id, work_date=cursor
                )
                if row is not None and getattr(row, "notes", None) == expected_note and getattr(row, "status", None) == "LEAVE":
                    # We can't reliably restore pre-leave punches without history, so revert to ABSENT and preserve auditability.
                    row.status = "ABSENT"
                    row.source = "MANUAL"
                    row.clock_in_at = None
                    row.clock_out_at = None
                    row.worked_minutes = 0
                    row.overtime_minutes = 0
                    row.payable_hours = Decimal("0")
                    row.notes = f"Leave cancelled {request.id}"
                    await self.attendance_repo.upsert_record(row)
                cursor = cursor + timedelta(days=1)

        if was_pending and decision in {"APPROVED", "REJECTED"}:
            emp = await self.employee_repo.get_by_id(org_id=org_id, employee_id=request.employee_id)
            lt = await self.leave_type_repo.get_by_id(org_id=org_id, leave_type_id=request.leave_type_id)
            emp_name = f"{emp.first_name} {emp.last_name}".strip() if emp else ""
            lt_name = lt.name if lt else ""
            auto_key = AUTOMATION_KEY_LEAVE_REQUEST_APPROVED if decision == "APPROVED" else AUTOMATION_KEY_LEAVE_REQUEST_REJECTED
            await try_emit_automation_announcement(
                self.leave_request_repo.db,
                org_id=org_id,
                actor_user_id=actor_user_id,
                automation_key=auto_key,
                dedupe_key=f"{auto_key}:{request.id}",
                variables={
                    "employee_name": emp_name,
                    "start_date": str(request.start_date),
                    "end_date": str(request.end_date),
                    "days": str(request.days or ""),
                    "leave_type_name": lt_name,
                    "reviewer_note": note or "",
                },
            )

