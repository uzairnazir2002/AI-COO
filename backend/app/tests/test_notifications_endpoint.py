import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeNotificationRepo:
    def __init__(self, db):
        self.db = db

    async def list_for_user(self, **kwargs):
        now = datetime.now(timezone.utc)
        item = SimpleNamespace(
            id=uuid.uuid4(),
            org_id=kwargs["org_id"],
            user_id=None,
            category="OPS",
            title="Queued",
            message="Something happened",
            link="/app/activity",
            is_read=False,
            metadata_json={"k": "v"},
            created_at=now,
        )
        return [item], 1

    async def mark_read(self, notification_id, *, user_id):
        return SimpleNamespace(id=notification_id, user_id=user_id)

    async def mark_all_read(self, *, user_id, org_id):
        return 3


@pytest.fixture
def notifications_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.api.v1.notifications as notifications

    return reload(notifications)


def _app_with_overrides(monkeypatch, module, org_id: uuid.UUID):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/notifications")

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="u@example.com")

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        return SimpleNamespace(org_id=org_id, role="OWNER")

    app.dependency_overrides[module.get_current_user] = fake_user
    app.dependency_overrides[module.get_db] = fake_db
    monkeypatch.setattr(module, "get_org_context", fake_ctx)
    monkeypatch.setattr(module, "NotificationRepo", FakeNotificationRepo)
    return app


def test_notifications_list_and_mark_read(monkeypatch, notifications_module):
    org_id = uuid.uuid4()
    client = TestClient(_app_with_overrides(monkeypatch, notifications_module, org_id))

    res = client.get(f"/api/v1/notifications?org_id={org_id}")
    assert res.status_code == 200
    assert res.json()["unread_count"] == 1

    notification_id = res.json()["items"][0]["id"]
    read_res = client.post(f"/api/v1/notifications/{notification_id}/read?org_id={org_id}")
    assert read_res.status_code == 200
    assert read_res.json()["ok"] is True


def test_notifications_mark_all(monkeypatch, notifications_module):
    org_id = uuid.uuid4()
    client = TestClient(_app_with_overrides(monkeypatch, notifications_module, org_id))

    res = client.post(f"/api/v1/notifications/read-all?org_id={org_id}")
    assert res.status_code == 200
    assert res.json()["updated"] == 3
