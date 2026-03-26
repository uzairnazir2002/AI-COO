from datetime import datetime, timezone
from importlib import reload
from types import SimpleNamespace
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeLocationService:
    listed: list[SimpleNamespace] = []
    created: SimpleNamespace | None = None

    def __init__(self, _repo):
        pass

    async def list_locations(self, org_id, *, include_inactive=False):
        _ = (org_id, include_inactive)
        return type(self).listed

    async def create_location(self, **_kwargs):
        assert type(self).created is not None
        return type(self).created


class _FakeAuditRepo:
    def __init__(self, _db):
        pass

    async def log(self, *_args, **_kwargs):
        return None


@pytest.fixture
def locations_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.locations as locations

    return reload(locations)


def _build_app(locations_module, monkeypatch, role="OWNER"):
    app = FastAPI()
    app.include_router(locations_module.router, prefix="/api/v1/locations")

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id=None, user=None, db=None):
        _ = (org_id, user, db)
        return SimpleNamespace(org_id=org_id, role=role)

    app.dependency_overrides[locations_module.get_current_user] = fake_user
    app.dependency_overrides[locations_module.get_db] = fake_db
    from app.api import deps as shared_deps

    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    monkeypatch.setattr(locations_module, "get_org_context", fake_ctx)
    monkeypatch.setattr(locations_module, "LocationService", _FakeLocationService)
    monkeypatch.setattr(locations_module, "LocationRepo", lambda _db: object())
    monkeypatch.setattr(locations_module, "AuditRepo", _FakeAuditRepo)
    return app


def test_list_locations_returns_payload(monkeypatch, locations_module):
    now = datetime.now(tz=timezone.utc)
    org_id = uuid.uuid4()
    _FakeLocationService.listed = [
        SimpleNamespace(
            id=uuid.uuid4(),
            org_id=org_id,
            created_by_user_id=uuid.uuid4(),
            name="Headquarters",
            code="HQ",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    ]
    app = _build_app(locations_module, monkeypatch, role="OWNER")
    client = TestClient(app)
    res = client.get(f"/api/v1/locations?org_id={org_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body) == 1
    assert body[0]["name"] == "Headquarters"


def test_create_location_forbidden_for_viewer(monkeypatch, locations_module):
    org_id = uuid.uuid4()
    _FakeLocationService.created = None
    app = _build_app(locations_module, monkeypatch, role="VIEWER")
    client = TestClient(app)
    res = client.post(
        "/api/v1/locations",
        json={"org_id": str(org_id), "name": "North", "code": "NTH", "is_active": True},
    )
    assert res.status_code == 403
