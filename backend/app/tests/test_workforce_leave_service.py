from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domain.services.workforce_leave_service import WorkforceLeaveService


class _FakeLeaveTypeRepo:
    async def get_by_id(self, **_kwargs):
        return SimpleNamespace(id=uuid.uuid4(), is_active=True, requires_approval=True)

    async def list_by_org(self, **_kwargs):
        return []

    async def get_by_name_or_code(self, **_kwargs):
        return None

    async def create(self, row):
        return row

    async def update(self, row):
        return row


class _FakeEmployeeRepo:
    async def get_by_id(self, **_kwargs):
        return SimpleNamespace(id=_kwargs["employee_id"], is_active=True)


class _FakeLeaveBalanceRepo:
    def __init__(self):
        self.bal = None

    async def get_balance(self, **_kwargs):
        return self.bal

    async def upsert(self, row):
        self.bal = row
        return row

    async def list_by_org(self, **_kwargs):
        return []


class _FakeLeaveRequestRepo:
    async def get_by_id(self, **_kwargs):
        return None

    async def list_by_org(self, **_kwargs):
        return []

    async def has_overlapping_approved(self, **_kwargs):
        return False

    async def create(self, row):
        return row

    async def update(self, row):
        return row


class _FakeAttendanceRepo:
    def __init__(self, record):
        self.record = record
        self.upserts = []

    async def get_record_for_date(self, **_kwargs):
        return self.record

    async def upsert_record(self, row):
        self.upserts.append(row)
        self.record = row
        return row


@pytest.mark.asyncio
async def test_cancelled_leave_reverts_leave_attendance_row():
    org_id = uuid.uuid4()
    actor_user_id = uuid.uuid4()
    employee_id = uuid.uuid4()
    leave_type_id = uuid.uuid4()
    req_id = uuid.uuid4()
    start = date(2026, 4, 10)
    end = date(2026, 4, 10)

    # Attendance row that was clearly created by leave approval
    att = SimpleNamespace(
        org_id=org_id,
        employee_id=employee_id,
        work_date=start,
        status="LEAVE",
        source="MANUAL",
        clock_in_at=None,
        clock_out_at=None,
        worked_minutes=0,
        overtime_minutes=0,
        payable_hours=Decimal("0"),
        notes=f"Leave {req_id}",
    )

    attendance_repo = _FakeAttendanceRepo(att)
    balance_repo = _FakeLeaveBalanceRepo()
    balance_repo.bal = SimpleNamespace(
        org_id=org_id,
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        year=2026,
        allocated_days=Decimal("10"),
        used_days=Decimal("1"),
        pending_days=Decimal("0"),
    )

    svc = WorkforceLeaveService(
        leave_type_repo=_FakeLeaveTypeRepo(),
        leave_balance_repo=balance_repo,
        leave_request_repo=_FakeLeaveRequestRepo(),
        employee_repo=_FakeEmployeeRepo(),
        attendance_repo=attendance_repo,
    )

    req = SimpleNamespace(
        id=req_id,
        org_id=org_id,
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        start_date=start,
        end_date=end,
        days=Decimal("1"),
        status="APPROVED",
        reviewed_by_user_id=None,
        reviewed_at=None,
        reviewer_note=None,
    )

    await svc._apply_decision(org_id=org_id, actor_user_id=actor_user_id, request=req, decision="CANCELLED", note="n/a")

    assert attendance_repo.upserts, "Expected attendance to be updated on cancellation"
    last = attendance_repo.upserts[-1]
    assert last.status == "ABSENT"
    assert last.notes == f"Leave cancelled {req_id}"

