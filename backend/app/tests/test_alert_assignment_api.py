from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps as shared_deps
import app.api.v1.alerts as alerts_module


class _FakeDb:
    async def commit(self):
        return None


class _FakeAlertRepo:
    def __init__(self, _db):
        self.alert = SimpleNamespace(
            id=uuid4(),
            org_id=uuid4(),
            kind="ANOMALY",
            severity="HIGH",
            title="Spike",
            description="Detected",
            meta={},
            status="OPEN",
            assigned_to_user_id=None,
            assigned_by_user_id=None,
            assigned_at=None,
            acknowledged_at=None,
            created_at=datetime.now(timezone.utc),
        )

    async def get(self, _alert_id, org_id):
        self.alert.org_id = org_id
        return self.alert


class _FakeAuditRepo:
    def __init__(self, _db):
        pass

    async def log(self, *_args, **_kwargs):
        return None

    async def list_entity_events(self, **_kwargs):
        return [
            SimpleNamespace(
                id=uuid4(),
                action="alert.assign",
                actor_user_id=uuid4(),
                metadata_json={"assigned_to_user_id": str(uuid4())},
                created_at=datetime.now(timezone.utc),
            )
        ]


class _FakeAlertsService:
    def __init__(self, _db, _repo):
        pass

    async def assign(self, *, alert, assignee_user_id, actor_user_id):
        alert.assigned_to_user_id = assignee_user_id
        alert.assigned_by_user_id = actor_user_id
        alert.assigned_at = datetime.now(timezone.utc)

    async def acknowledge(self, *, alert):
        alert.acknowledged_at = datetime.now(timezone.utc)


def _build_app(monkeypatch, *, assignee_is_member: bool):
    app = FastAPI()
    app.include_router(alerts_module.router, prefix="/api/v1/alerts")

    async def fake_user():
        return SimpleNamespace(id=uuid4(), email="owner@example.com", is_active=True)

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id=None, user=None, db=None):
        _ = (user, db)
        return SimpleNamespace(org_id=org_id, role="OWNER")

    class _FakeOrgRepo:
        def __init__(self, _db):
            pass

        async def membership(self, _user_id, _org_id):
            return SimpleNamespace(role="EDITOR") if assignee_is_member else None

    monkeypatch.setattr(alerts_module, "AlertRepo", _FakeAlertRepo)
    monkeypatch.setattr(alerts_module, "AlertsService", _FakeAlertsService)
    monkeypatch.setattr(alerts_module, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(alerts_module, "OrgRepo", _FakeOrgRepo)

    async def _noop_cache_delete(_prefix):
        return None

    monkeypatch.setattr(alerts_module, "cache_delete_prefix", _noop_cache_delete)

    app.dependency_overrides[shared_deps.get_current_user] = fake_user
    app.dependency_overrides[shared_deps.get_db] = fake_db
    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    app.dependency_overrides[alerts_module.get_current_user] = fake_user
    app.dependency_overrides[alerts_module.get_db] = fake_db
    app.dependency_overrides[alerts_module.get_org_context] = fake_ctx
    alerts_module.get_org_context = fake_ctx
    return app


def test_assign_alert_rejects_non_member_assignee(monkeypatch):
    app = _build_app(monkeypatch, assignee_is_member=False)
    client = TestClient(app)
    response = client.post(
        f"/api/v1/alerts/{uuid4()}/assign",
        json={"org_id": str(uuid4()), "assignee_user_id": str(uuid4())},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Assignee is not a member of organization"


def test_acknowledge_alert_sets_acknowledged_timestamp(monkeypatch):
    app = _build_app(monkeypatch, assignee_is_member=True)
    client = TestClient(app)
    response = client.post(
        f"/api/v1/alerts/{uuid4()}/acknowledge",
        json={"org_id": str(uuid4())},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["alert"]["acknowledged_at"] is not None


def test_alert_history_returns_assignment_events(monkeypatch):
    app = _build_app(monkeypatch, assignee_is_member=True)
    client = TestClient(app)
    response = client.get(f"/api/v1/alerts/{uuid4()}/history?org_id={uuid4()}")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["action"] == "alert.assign"


def test_assign_alert_accepts_legacy_query_payload(monkeypatch):
    app = _build_app(monkeypatch, assignee_is_member=True)
    client = TestClient(app)
    org_id = uuid4()
    assignee_id = uuid4()
    response = client.post(
        f"/api/v1/alerts/{uuid4()}/assign?org_id={org_id}&assignee_user_id={assignee_id}",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["alert"]["assigned_to_user_id"] == str(assignee_id)


def test_acknowledge_alert_accepts_legacy_query_payload(monkeypatch):
    app = _build_app(monkeypatch, assignee_is_member=True)
    client = TestClient(app)
    response = client.post(
        f"/api/v1/alerts/{uuid4()}/acknowledge?org_id={uuid4()}",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["alert"]["acknowledged_at"] is not None
