from datetime import date, datetime, time, timezone
from importlib import reload
from types import SimpleNamespace
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeAuditRepo:
    def __init__(self, _db):
        pass

    async def log(self, *_args, **_kwargs):
        return None


class _FakeShiftService:
    listed: list[SimpleNamespace] = []

    def __init__(self, **_kwargs):
        pass

    async def list_shifts(self, **_kwargs):
        _ = _kwargs
        return type(self).listed


class _FakeAttendanceService:
    clocked_in: SimpleNamespace | None = None
    clocked_out: SimpleNamespace | None = None
    daily_items: list[SimpleNamespace] = []
    calendar_out: dict | None = None
    correction_list: list[SimpleNamespace] = []
    correction_row: SimpleNamespace | None = None

    def __init__(self, **_kwargs):
        pass

    async def clock_in(self, **_kwargs):
        if type(self).clocked_in is None:
            raise ValueError("Employee not found")
        return type(self).clocked_in

    async def clock_out(self, **_kwargs):
        if type(self).clocked_out is None:
            raise ValueError("Cannot clock out without a clock-in for this date")
        return type(self).clocked_out

    async def daily_view(self, **_kwargs):
        _ = _kwargs
        return type(self).daily_items

    async def calendar_month(self, **_kwargs):
        if type(self).calendar_out is None:
            raise ValueError("month must be YYYY-MM")
        return type(self).calendar_out

    async def request_correction(self, **_kwargs):
        if type(self).correction_row is None:
            from app.domain.services.errors import NotFoundError

            raise NotFoundError("Attendance record not found")
        return type(self).correction_row

    async def review_correction(self, **_kwargs):
        if type(self).correction_row is None:
            from app.domain.services.errors import NotFoundError

            raise NotFoundError("Correction not found")
        return type(self).correction_row


@pytest.fixture
def attendance_modules(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.workforce.attendance as attendance
    import app.api.v1.workforce.corrections as corrections
    import app.api.v1.workforce.shifts as shifts

    return reload(attendance), reload(corrections), reload(shifts)


def _build_app(*, monkeypatch, attendance_modules, role="OWNER"):
    attendance, corrections, shifts = attendance_modules
    app = FastAPI()
    app.include_router(attendance.router, prefix="/api/v1/workforce/attendance")
    app.include_router(corrections.router, prefix="/api/v1/workforce/corrections")
    app.include_router(shifts.router, prefix="/api/v1/workforce/shifts")

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com", is_active=True)

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id=None, user=None, db=None):
        _ = (org_id, user, db)
        return SimpleNamespace(org_id=org_id, role=role)

    for module in (attendance, corrections, shifts):
        app.dependency_overrides[module.get_current_user] = fake_user
        app.dependency_overrides[module.get_db] = fake_db
        monkeypatch.setattr(module, "get_org_context", fake_ctx)

    monkeypatch.setattr(attendance, "WorkforceAttendanceService", _FakeAttendanceService)
    monkeypatch.setattr(attendance, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(attendance, "WorkforceAttendanceRepo", lambda _db: object())
    monkeypatch.setattr(attendance, "WorkforceEmployeeRepo", lambda _db: object())
    monkeypatch.setattr(attendance, "WorkforceShiftRepo", lambda _db: object())

    monkeypatch.setattr(corrections, "WorkforceAttendanceService", _FakeAttendanceService)
    monkeypatch.setattr(corrections, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(corrections, "WorkforceAttendanceRepo", lambda _db: object())
    monkeypatch.setattr(corrections, "WorkforceEmployeeRepo", lambda _db: object())
    monkeypatch.setattr(corrections, "WorkforceShiftRepo", lambda _db: object())

    monkeypatch.setattr(shifts, "WorkforceShiftService", _FakeShiftService)
    monkeypatch.setattr(shifts, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(shifts, "WorkforceShiftRepo", lambda _db: object())
    monkeypatch.setattr(shifts, "WorkforceEmployeeRepo", lambda _db: object())

    return app


def _attendance_row(org_id: uuid.UUID, employee_id: uuid.UUID, work_date: date, now: datetime):
    return SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        employee_id=employee_id,
        created_by_user_id=uuid.uuid4(),
        work_date=work_date,
        status="PRESENT",
        source="CLOCK",
        shift_id=None,
        shift_assignment_id=None,
        clock_in_at=now,
        clock_out_at=None,
        is_late=False,
        minutes_late=0,
        missing_checkout=True,
        worked_minutes=0,
        overtime_minutes=0,
        payable_hours="0",
        notes=None,
        created_at=now,
        updated_at=now,
    )


def test_clock_in_forbidden_for_viewer(monkeypatch, attendance_modules):
    app = _build_app(monkeypatch=monkeypatch, attendance_modules=attendance_modules, role="VIEWER")
    client = TestClient(app)
    res = client.post(
        "/api/v1/workforce/attendance/clock-in",
        json={"org_id": str(uuid.uuid4()), "employee_id": str(uuid.uuid4())},
    )
    assert res.status_code == 403


def test_clock_out_requires_clock_in(monkeypatch, attendance_modules):
    app = _build_app(monkeypatch=monkeypatch, attendance_modules=attendance_modules, role="OWNER")
    client = TestClient(app)
    _FakeAttendanceService.clocked_out = None
    res = client.post(
        "/api/v1/workforce/attendance/clock-out",
        json={"org_id": str(uuid.uuid4()), "employee_id": str(uuid.uuid4())},
    )
    assert res.status_code == 422


def test_daily_view_returns_items(monkeypatch, attendance_modules):
    org_id = uuid.uuid4()
    employee_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    d = date(2026, 4, 10)
    _FakeAttendanceService.daily_items = [_attendance_row(org_id, employee_id, d, now)]
    app = _build_app(monkeypatch=monkeypatch, attendance_modules=attendance_modules, role="OWNER")
    client = TestClient(app)
    res = client.get(f"/api/v1/workforce/attendance/daily?org_id={org_id}&date={d.isoformat()}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["org_id"] == str(org_id)
    assert body["date"] == d.isoformat()
    assert len(body["items"]) == 1


def test_calendar_rejects_invalid_month(monkeypatch, attendance_modules):
    app = _build_app(monkeypatch=monkeypatch, attendance_modules=attendance_modules, role="OWNER")
    client = TestClient(app)
    _FakeAttendanceService.calendar_out = None
    res = client.get(f"/api/v1/workforce/attendance/calendar?org_id={uuid.uuid4()}&month=2026-13")
    assert res.status_code == 422


def test_correction_request_forbidden_for_viewer(monkeypatch, attendance_modules):
    app = _build_app(monkeypatch=monkeypatch, attendance_modules=attendance_modules, role="VIEWER")
    client = TestClient(app)
    res = client.post(
        "/api/v1/workforce/corrections",
        json={"org_id": str(uuid.uuid4()), "attendance_record_id": str(uuid.uuid4()), "reason": "Fix punch"},
    )
    assert res.status_code == 403


def test_correction_review_404(monkeypatch, attendance_modules):
    app = _build_app(monkeypatch=monkeypatch, attendance_modules=attendance_modules, role="OWNER")
    client = TestClient(app)
    _FakeAttendanceService.correction_row = None
    res = client.post(
        f"/api/v1/workforce/corrections/{uuid.uuid4()}/review",
        json={"org_id": str(uuid.uuid4()), "status": "APPROVED"},
    )
    assert res.status_code == 404

