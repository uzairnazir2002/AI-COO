from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import deps as shared_deps
from app.api.v1 import alerts, jobs, reports, transactions


def _build_app(allowed_org_id):
    app = FastAPI()
    app.include_router(alerts.router, prefix="/api/v1/alerts")
    app.include_router(reports.router, prefix="/api/v1/reports")
    app.include_router(transactions.router, prefix="/api/v1/transactions")
    app.include_router(jobs.router, prefix="/api/v1/jobs")

    async def fake_user():
        return SimpleNamespace(id=uuid4(), email="owner@example.com", is_active=True)

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_db():
        yield _FakeDb()

    async def fake_org_context(org_id, user=None, db=None):
        _ = (user, db)
        if org_id != allowed_org_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        return SimpleNamespace(org_id=org_id, role="OWNER")

    app.dependency_overrides[shared_deps.get_current_user] = fake_user
    app.dependency_overrides[shared_deps.get_db] = fake_db
    app.dependency_overrides[shared_deps.get_org_context] = fake_org_context
    for module in (alerts, reports, transactions, jobs):
        app.dependency_overrides[module.get_current_user] = fake_user
        app.dependency_overrides[module.get_db] = fake_db
        app.dependency_overrides[module.get_org_context] = fake_org_context
        module.get_org_context = fake_org_context
    return app


def test_cross_org_requests_are_rejected():
    allowed_org_id = uuid4()
    blocked_org_id = uuid4()
    client = TestClient(_build_app(allowed_org_id))

    responses = [
        client.get(f"/api/v1/alerts?org_id={blocked_org_id}"),
        client.get(f"/api/v1/reports?org_id={blocked_org_id}"),
        client.get(f"/api/v1/transactions?org_id={blocked_org_id}&page=1&page_size=20"),
        client.get(f"/api/v1/transactions/import-profiles?org_id={blocked_org_id}"),
        client.get(f"/api/v1/jobs?org_id={blocked_org_id}&page=1&page_size=20"),
    ]

    for response in responses:
        assert response.status_code == 403
        assert response.json()["detail"] == "Forbidden"
