import uuid
from datetime import date
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


def test_plan_usage_endpoint(monkeypatch, organizations_module):
    org_id = uuid.uuid4()

    class _UsageService:
        def __init__(self, _repo):
            pass

        async def get_usage_overview(self, _org_id):
            return {
                "plan_code": "FREE",
                "period_start": date(2026, 3, 1),
                "metrics": {
                    "transactions": {"used": 10, "limit": 10000},
                    "reports": {"used": 1, "limit": 20},
                    "ai_summaries": {"used": 3, "limit": 500},
                },
            }

    app = FastAPI()
    app.include_router(organizations_module.router, prefix="/api/v1/organizations")

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="u@example.com")

    async def fake_db():
        yield object()

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        return SimpleNamespace(org_id=org_id, role="OWNER")

    app.dependency_overrides[organizations_module.get_current_user] = fake_user
    app.dependency_overrides[organizations_module.get_db] = fake_db
    monkeypatch.setattr(organizations_module, "get_org_context", fake_ctx)
    monkeypatch.setattr(organizations_module, "UsageService", _UsageService)

    client = TestClient(app)
    res = client.get(f"/api/v1/organizations/{org_id}/plan-usage")
    assert res.status_code == 200
    body = res.json()
    assert body["plan_code"] == "FREE"
    assert body["metrics"]["transactions"]["used"] == 10
