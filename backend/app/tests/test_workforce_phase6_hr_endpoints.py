import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps as api_deps
from app.db import session as db_session


@pytest.fixture()
def _fake_user():
    return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com", is_active=True)


def _build_app(monkeypatch, workforce_modules, role: str):
    employees_mod, hr_mod = workforce_modules

    async def _fake_get_current_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com", is_active=True)

    async def _fake_get_org_context(org_id, user, db):
        return SimpleNamespace(org_id=org_id, role=role)

    class _FakeDb:
        async def commit(self):  # pragma: no cover
            return None

    async def _fake_get_db():
        yield _FakeDb()

    app = FastAPI()
    app.include_router(employees_mod.router, prefix="/api/v1/workforce/employees")
    app.include_router(hr_mod.router, prefix="/api/v1/workforce/hr")
    app.dependency_overrides[api_deps.get_current_user] = _fake_get_current_user
    app.dependency_overrides[db_session.get_db] = _fake_get_db
    monkeypatch.setattr(hr_mod, "get_org_context", _fake_get_org_context)
    return app


@pytest.fixture()
def workforce_modules():
    from app.api.v1.workforce import employees, hr_admin

    return employees, hr_admin


def test_hr_policy_create_forbidden_for_viewer(monkeypatch, workforce_modules):
    app = _build_app(monkeypatch=monkeypatch, workforce_modules=workforce_modules, role="VIEWER")
    client = TestClient(app)
    org_id = str(uuid.uuid4())
    res = client.post(
        "/api/v1/workforce/hr/policies",
        json={"org_id": org_id, "code": "SAFETY", "title": "Safety", "body": "Body", "publish_now": True},
    )
    assert res.status_code == 403


def test_hr_checklist_create_forbidden_for_viewer(monkeypatch, workforce_modules):
    app = _build_app(monkeypatch=monkeypatch, workforce_modules=workforce_modules, role="VIEWER")
    client = TestClient(app)
    org_id = str(uuid.uuid4())
    res = client.post(
        "/api/v1/workforce/hr/checklist",
        json={"org_id": org_id, "employee_id": str(uuid.uuid4()), "kind": "ONBOARDING", "title": "Setup payroll"},
    )
    assert res.status_code == 403

