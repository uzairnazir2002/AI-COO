import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def organizations_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.api.v1.organizations as organizations

    return reload(organizations)


def _app_with_overrides(monkeypatch, organizations_module, role: str, ctx_org_id: uuid.UUID, service):
    app = FastAPI()
    app.include_router(organizations_module.router, prefix="/api/v1/organizations")

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")

    class _FakeDB:
        async def commit(self):
            return None

        async def execute(self, *_args, **_kwargs):
            return SimpleNamespace(scalar_one_or_none=lambda: SimpleNamespace(sensitive_action_reauth_minutes=30))

    async def fake_db():
        yield _FakeDB()

    async def fake_ctx(org_id: uuid.UUID, user=None, request=None, db=None):
        _ = (org_id, user, request, db)
        return SimpleNamespace(org_id=ctx_org_id, role=role)

    app.dependency_overrides[organizations_module.get_current_user] = fake_user
    app.dependency_overrides[organizations_module.get_db] = fake_db
    app.dependency_overrides[organizations_module.get_org_context] = fake_ctx
    from app.api import deps as shared_deps

    app.dependency_overrides[shared_deps.get_db] = fake_db
    app.dependency_overrides[shared_deps.get_current_user] = fake_user
    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    monkeypatch.setattr(shared_deps, "get_org_context", fake_ctx)
    monkeypatch.setattr(organizations_module, "get_org_context", fake_ctx)
    monkeypatch.setattr(organizations_module, "OrgService", lambda *args, **kwargs: service)
    return app


def _billing_obj(org_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        billing_email="billing@example.com",
        invoice_enabled=True,
        plan_label="Scale",
        billing_notes="Owner managed",
    )


def test_billing_get_and_put_owner_only_success(monkeypatch, organizations_module):
    org_id = uuid.uuid4()
    billing = _billing_obj(org_id)

    class _Svc:
        async def get_billing(self, _org_id):
            return billing

        async def update_billing(
            self, actor_user_id, org_id, billing_email, invoice_enabled, plan_label, billing_notes
        ):
            billing.billing_email = billing_email
            billing.invoice_enabled = invoice_enabled
            billing.plan_label = plan_label
            billing.billing_notes = billing_notes
            return billing

    app = _app_with_overrides(monkeypatch, organizations_module, "OWNER", org_id, _Svc())
    client = TestClient(app)

    get_res = client.get(f"/api/v1/organizations/{org_id}/billing")
    assert get_res.status_code == 200
    assert get_res.json()["billing_email"] == "billing@example.com"

    put_res = client.put(
        f"/api/v1/organizations/{org_id}/billing",
        json={
            "billing_email": "finance@example.com",
            "invoice_enabled": False,
            "plan_label": "Enterprise",
            "billing_notes": "Updated",
        },
    )
    assert put_res.status_code == 200
    assert put_res.json()["billing_email"] == "finance@example.com"
    assert put_res.json()["invoice_enabled"] is False


def test_billing_editor_forbidden(monkeypatch, organizations_module):
    org_id = uuid.uuid4()

    class _Svc:
        async def get_billing(self, _org_id):
            return _billing_obj(org_id)

    app = _app_with_overrides(monkeypatch, organizations_module, "EDITOR", org_id, _Svc())
    client = TestClient(app)

    res = client.get(f"/api/v1/organizations/{org_id}/billing")
    assert res.status_code == 403


def test_org_delete_request_owner(monkeypatch, organizations_module):
    org_id = uuid.uuid4()

    class _Svc:
        async def get_billing(self, _org_id):
            return _billing_obj(org_id)

    class _FakePrivacyService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def request_org_deletion(self, *, actor_user_id, org_id, reason):
            _ = (actor_user_id, org_id, reason)
            return {"request_id": uuid.uuid4(), "delete_after": "2026-04-01T00:00:00Z"}

    monkeypatch.setattr(organizations_module, "PrivacyService", _FakePrivacyService)
    app = _app_with_overrides(monkeypatch, organizations_module, "OWNER", org_id, _Svc())
    client = TestClient(app)

    res = client.post(f"/api/v1/organizations/{org_id}/delete", json={"reason": "close business"})
    assert res.status_code == 200
    assert res.json()["ok"] is True
