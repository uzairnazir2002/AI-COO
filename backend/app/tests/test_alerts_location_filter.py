from datetime import datetime, timezone
from importlib import reload
from types import SimpleNamespace
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app(module):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/alerts")

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id=None, user=None, db=None):
        _ = (user, db)
        return SimpleNamespace(org_id=org_id, role="OWNER")

    app.dependency_overrides[module.get_current_user] = fake_user
    app.dependency_overrides[module.get_db] = fake_db
    app.dependency_overrides[module.get_org_context] = fake_ctx
    module.get_org_context = fake_ctx
    return app


def test_list_alerts_passes_location_filter(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.alerts as alerts_module

    alerts_module = reload(alerts_module)
    observed: dict[str, object] = {}

    class _FakeLocationService:
        def __init__(self, _repo):
            pass

        async def ensure_org_location(self, *, org_id, location_id, require_active=True):
            observed["validated_org_id"] = org_id
            observed["validated_location_id"] = location_id
            observed["require_active"] = require_active
            return None

    class _FakeAlertsService:
        def __init__(self, _db, _repo):
            pass

        async def list_alerts(self, _org_id, _status, assigned_to_user_id=None, location_id=None):
            observed["list_location_id"] = location_id
            observed["assigned_to_user_id"] = assigned_to_user_id
            return [
                SimpleNamespace(
                    id=uuid.uuid4(),
                    org_id=_org_id,
                    location_id=location_id,
                    kind="ANOMALY",
                    severity="HIGH",
                    title="Location spike",
                    description="Detected",
                    meta={},
                    status="OPEN",
                    created_at=datetime.now(timezone.utc),
                )
            ]

    async def fake_cache_get(_key):
        return None

    async def fake_cache_set(_key, _payload, _ttl):
        return None

    monkeypatch.setattr(alerts_module, "LocationService", _FakeLocationService)
    monkeypatch.setattr(alerts_module, "AlertsService", _FakeAlertsService)
    monkeypatch.setattr(alerts_module, "cache_get_json", fake_cache_get)
    monkeypatch.setattr(alerts_module, "cache_set_json", fake_cache_set)

    app = _build_app(alerts_module)
    client = TestClient(app)
    org_id = uuid.uuid4()
    location_id = uuid.uuid4()

    response = client.get(
        f"/api/v1/alerts?org_id={org_id}&status=OPEN&location_id={location_id}"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["items"][0]["location_id"] == str(location_id)
    assert observed["validated_org_id"] == org_id
    assert observed["validated_location_id"] == location_id
    assert observed["list_location_id"] == location_id
