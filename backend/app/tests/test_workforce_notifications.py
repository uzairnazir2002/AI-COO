from datetime import date, datetime, timezone
from decimal import Decimal
from importlib import reload
from types import SimpleNamespace
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeAuditRepo:
    def __init__(self, _db):
        pass

    async def log(self, *_args, **_kwargs):
        return None


def _fake_db_dep():
    class _FakeDb:
        async def commit(self):
            return None

    async def _dep():
        yield _FakeDb()

    return _dep


def _fake_user_dep():
    async def _dep():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com", is_active=True)

    return _dep


def _fake_ctx_dep(role: str):
    async def _dep(org_id=None, user=None, db=None):
        _ = (user, db)
        return SimpleNamespace(org_id=org_id, role=role)

    return _dep


def test_leave_decision_emits_notification(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.workforce.leave as leave_module

    leave_module = reload(leave_module)
    app = FastAPI()
    app.include_router(leave_module.router, prefix="/api/v1/workforce/leave")
    app.dependency_overrides[leave_module.get_current_user] = _fake_user_dep()
    app.dependency_overrides[leave_module.get_db] = _fake_db_dep()
    monkeypatch.setattr(leave_module, "get_org_context", _fake_ctx_dep("OWNER"))
    monkeypatch.setattr(leave_module, "AuditRepo", _FakeAuditRepo)

    now = datetime.now(tz=timezone.utc)
    row = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        created_by_user_id=uuid.uuid4(),
        employee_id=uuid.uuid4(),
        leave_type_id=uuid.uuid4(),
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        days=Decimal("1.00"),
        status="APPROVED",
        reason=None,
        reviewed_by_user_id=uuid.uuid4(),
        reviewed_at=now,
        reviewer_note=None,
        created_at=now,
        updated_at=now,
    )

    class _Svc:
        async def decide_request(self, **_kwargs):
            return row

    calls: list[dict] = []

    async def _notify(_db, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(leave_module, "_svc", lambda _db: _Svc())
    monkeypatch.setattr(leave_module, "_notify_workforce_event", _notify)

    client = TestClient(app)
    org_id = uuid.uuid4()
    res = client.post(
        f"/api/v1/workforce/leave/requests/{uuid.uuid4()}/decision",
        json={"org_id": str(org_id), "status": "APPROVED"},
    )
    assert res.status_code == 200
    assert calls and calls[0]["org_id"] == org_id


def test_payroll_mark_paid_emits_notification(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.workforce.payroll as payroll_module

    payroll_module = reload(payroll_module)
    app = FastAPI()
    app.include_router(payroll_module.router, prefix="/api/v1/workforce/payroll")
    app.dependency_overrides[payroll_module.get_current_user] = _fake_user_dep()
    app.dependency_overrides[payroll_module.get_db] = _fake_db_dep()
    from app.api import deps as shared_deps
    app.dependency_overrides[shared_deps.get_db] = _fake_db_dep()
    app.dependency_overrides[shared_deps.get_current_user] = _fake_user_dep()
    monkeypatch.setattr(payroll_module, "get_org_context", _fake_ctx_dep("OWNER"))
    monkeypatch.setattr(payroll_module, "AuditRepo", _FakeAuditRepo)

    now = datetime.now(tz=timezone.utc)
    period = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        created_by_user_id=uuid.uuid4(),
        start_date=now.date(),
        end_date=now.date(),
        status="PAID",
        approved_by_user_id=None,
        approved_at=None,
        paid_by_user_id=uuid.uuid4(),
        paid_at=now,
        created_at=now,
        updated_at=now,
    )

    class _Svc:
        async def mark_paid(self, **_kwargs):
            return period

    calls: list[dict] = []

    async def _notify(_db, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(payroll_module, "_svc", lambda _db: _Svc())
    monkeypatch.setattr(payroll_module, "_notify_workforce_event", _notify)

    client = TestClient(app)
    res = client.post(
        f"/api/v1/workforce/payroll/periods/{period.id}/mark-paid",
        json={"org_id": str(period.org_id)},
    )
    assert res.status_code == 200
    assert calls and calls[0]["org_id"] == period.org_id


def test_hr_checklist_done_emits_notification(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.workforce.hr_admin as hr_module

    hr_module = reload(hr_module)
    app = FastAPI()
    app.include_router(hr_module.router, prefix="/api/v1/workforce/hr")
    app.dependency_overrides[hr_module.get_current_user] = _fake_user_dep()
    app.dependency_overrides[hr_module.get_db] = _fake_db_dep()
    monkeypatch.setattr(hr_module, "get_org_context", _fake_ctx_dep("OWNER"))
    monkeypatch.setattr(hr_module, "AuditRepo", _FakeAuditRepo)

    item = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        employee_id=uuid.uuid4(),
        kind="ONBOARDING",
        title="Complete payroll setup",
        details=None,
        due_date=None,
        is_done=True,
        completed_at=datetime.now(tz=timezone.utc),
        completed_by_user_id=uuid.uuid4(),
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )

    class _Svc:
        async def set_checklist_done(self, **_kwargs):
            return item

    calls: list[dict] = []

    async def _notify(_db, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(hr_module, "_svc", lambda _db: _Svc())
    monkeypatch.setattr(hr_module, "_notify_workforce_event", _notify)

    client = TestClient(app)
    res = client.post(
        f"/api/v1/workforce/hr/checklist/{item.id}/done",
        json={"org_id": str(item.org_id), "is_done": True},
    )
    assert res.status_code == 200
    assert calls and calls[0]["org_id"] == item.org_id
