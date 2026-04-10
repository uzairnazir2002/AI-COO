from datetime import date, datetime, timezone
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


class _FakeLeaveService:
    leave_types: list[SimpleNamespace] = []
    balances: list[SimpleNamespace] = []
    requests: list[SimpleNamespace] = []
    created_type: SimpleNamespace | None = None
    created_request: SimpleNamespace | None = None
    decided_request: SimpleNamespace | None = None

    def __init__(self, **_kwargs):
        pass

    async def list_leave_types(self, **_kwargs):
        return type(self).leave_types

    async def create_leave_type(self, **_kwargs):
        if type(self).created_type is None:
            raise ValueError("bad")
        return type(self).created_type

    async def update_leave_type(self, **_kwargs):
        if type(self).created_type is None:
            from app.domain.services.errors import NotFoundError

            raise NotFoundError("Leave type not found")
        return type(self).created_type

    async def deactivate_leave_type(self, **_kwargs):
        if type(self).created_type is None:
            from app.domain.services.errors import NotFoundError

            raise NotFoundError("Leave type not found")
        return type(self).created_type

    async def list_balances(self, **_kwargs):
        return type(self).balances

    async def allocate_balance(self, **_kwargs):
        if type(self).balances:
            return type(self).balances[0]
        raise ValueError("bad")

    async def list_requests(self, **_kwargs):
        return type(self).requests

    async def create_request(self, **_kwargs):
        if type(self).created_request is None:
            raise ValueError("bad")
        return type(self).created_request

    async def decide_request(self, **_kwargs):
        if type(self).decided_request is None:
            from app.domain.services.errors import NotFoundError

            raise NotFoundError("Leave request not found")
        return type(self).decided_request


@pytest.fixture
def leave_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.workforce.leave as leave

    return reload(leave)


def _build_app(*, monkeypatch, leave_module, role="OWNER"):
    app = FastAPI()
    app.include_router(leave_module.router, prefix="/api/v1/workforce/leave")

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="user@example.com", is_active=True)

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id=None, user=None, db=None):
        _ = (org_id, user, db)
        return SimpleNamespace(org_id=org_id, role=role)

    app.dependency_overrides[leave_module.get_current_user] = fake_user
    app.dependency_overrides[leave_module.get_db] = fake_db
    monkeypatch.setattr(leave_module, "get_org_context", fake_ctx)
    monkeypatch.setattr(leave_module, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(leave_module, "_svc", lambda _db: _FakeLeaveService())

    return app


def test_leave_type_create_forbidden_for_viewer(monkeypatch, leave_module):
    app = _build_app(monkeypatch=monkeypatch, leave_module=leave_module, role="VIEWER")
    client = TestClient(app)
    res = client.post(
        "/api/v1/workforce/leave/types",
        json={"org_id": str(uuid.uuid4()), "name": "Annual", "code": "AL"},
    )
    assert res.status_code == 403


def test_leave_types_list_ok(monkeypatch, leave_module):
    org_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    _FakeLeaveService.leave_types = [
        SimpleNamespace(
            id=uuid.uuid4(),
            org_id=org_id,
            created_by_user_id=uuid.uuid4(),
            name="Annual",
            code="AL",
            is_paid=True,
            requires_approval=True,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    ]
    app = _build_app(monkeypatch=monkeypatch, leave_module=leave_module, role="OWNER")
    client = TestClient(app)
    res = client.get(f"/api/v1/workforce/leave/types?org_id={org_id}")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_leave_request_decision_404(monkeypatch, leave_module):
    app = _build_app(monkeypatch=monkeypatch, leave_module=leave_module, role="OWNER")
    client = TestClient(app)
    _FakeLeaveService.decided_request = None
    res = client.post(
        f"/api/v1/workforce/leave/requests/{uuid.uuid4()}/decision",
        json={"org_id": str(uuid.uuid4()), "status": "APPROVED"},
    )
    assert res.status_code == 404


def test_leave_request_create_422(monkeypatch, leave_module):
    app = _build_app(monkeypatch=monkeypatch, leave_module=leave_module, role="OWNER")
    client = TestClient(app)
    _FakeLeaveService.created_request = None
    res = client.post(
        "/api/v1/workforce/leave/requests",
        json={
            "org_id": str(uuid.uuid4()),
            "employee_id": str(uuid.uuid4()),
            "leave_type_id": str(uuid.uuid4()),
            "start_date": date(2026, 4, 10).isoformat(),
            "end_date": date(2026, 4, 9).isoformat(),
            "days": "1",
        },
    )
    assert res.status_code in {422, 400}

