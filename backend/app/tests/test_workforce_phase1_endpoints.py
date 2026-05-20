from datetime import date, datetime, timezone
from decimal import Decimal
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


class _FakeLocationService:
    async def ensure_org_location(self, *, org_id, location_id, require_active=True):
        _ = (org_id, location_id, require_active)
        return None


class _FakeEmployeeService:
    listed: list[SimpleNamespace] = []
    got: SimpleNamespace | None = None
    created: SimpleNamespace | None = None
    updated: SimpleNamespace | None = None
    deactivated: SimpleNamespace | None = None

    def __init__(self, **_kwargs):
        pass

    async def list_employees(self, **_kwargs):
        _ = _kwargs
        return type(self).listed

    async def get_employee(self, **_kwargs):
        assert type(self).got is not None
        return type(self).got

    async def create_employee(self, **_kwargs):
        assert type(self).created is not None
        return type(self).created

    async def update_employee(self, **_kwargs):
        assert type(self).updated is not None
        return type(self).updated

    async def deactivate_employee(self, **_kwargs):
        assert type(self).deactivated is not None
        return type(self).deactivated


class _FakeDepartmentService:
    listed: list[SimpleNamespace] = []
    created: SimpleNamespace | None = None

    def __init__(self, _repo):
        pass

    async def list_departments(self, **_kwargs):
        _ = _kwargs
        return type(self).listed

    async def create_department(self, **_kwargs):
        assert type(self).created is not None
        return type(self).created


class _FakeTitleService:
    listed: list[SimpleNamespace] = []
    created: SimpleNamespace | None = None

    def __init__(self, _repo):
        pass

    async def list_titles(self, **_kwargs):
        _ = _kwargs
        return type(self).listed

    async def create_title(self, **_kwargs):
        assert type(self).created is not None
        return type(self).created


@pytest.fixture
def workforce_modules(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.workforce.employees as employees
    import app.api.v1.workforce.departments as departments
    import app.api.v1.workforce.titles as titles

    return reload(employees), reload(departments), reload(titles)


def _build_app(*, monkeypatch, workforce_modules, role="OWNER"):
    employees, departments, titles = workforce_modules
    app = FastAPI()
    app.include_router(employees.router, prefix="/api/v1/workforce/employees")
    app.include_router(departments.router, prefix="/api/v1/workforce/departments")
    app.include_router(titles.router, prefix="/api/v1/workforce/titles")

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com", is_active=True)

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id=None, user=None, db=None):
        _ = (org_id, user, db)
        return SimpleNamespace(org_id=org_id, role=role)

    for module in (employees, departments, titles):
        app.dependency_overrides[module.get_current_user] = fake_user
        app.dependency_overrides[module.get_db] = fake_db
        monkeypatch.setattr(module, "get_org_context", fake_ctx)

    monkeypatch.setattr(employees, "WorkforceEmployeeService", _FakeEmployeeService)
    monkeypatch.setattr(employees, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(employees, "LocationService", lambda _repo: _FakeLocationService())
    monkeypatch.setattr(employees, "LocationRepo", lambda _db: object())
    monkeypatch.setattr(employees, "WorkforceEmployeeRepo", lambda _db: object())
    monkeypatch.setattr(employees, "WorkforceDepartmentRepo", lambda _db: object())
    monkeypatch.setattr(employees, "WorkforceTitleRepo", lambda _db: object())

    monkeypatch.setattr(departments, "WorkforceDepartmentService", _FakeDepartmentService)
    monkeypatch.setattr(departments, "WorkforceDepartmentRepo", lambda _db: object())
    monkeypatch.setattr(departments, "AuditRepo", _FakeAuditRepo)

    monkeypatch.setattr(titles, "WorkforceTitleService", _FakeTitleService)
    monkeypatch.setattr(titles, "WorkforceTitleRepo", lambda _db: object())
    monkeypatch.setattr(titles, "AuditRepo", _FakeAuditRepo)

    return app


def _build_isolation_app(*, monkeypatch, workforce_modules, allowed_org_id):
    employees, departments, titles = workforce_modules
    app = FastAPI()
    app.include_router(employees.router, prefix="/api/v1/workforce/employees")
    app.include_router(departments.router, prefix="/api/v1/workforce/departments")
    app.include_router(titles.router, prefix="/api/v1/workforce/titles")

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com", is_active=True)

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id=None, user=None, db=None):
        _ = (user, db)
        if org_id != allowed_org_id:
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="Forbidden")
        return SimpleNamespace(org_id=org_id, role="OWNER")

    for module in (employees, departments, titles):
        app.dependency_overrides[module.get_current_user] = fake_user
        app.dependency_overrides[module.get_db] = fake_db
        monkeypatch.setattr(module, "get_org_context", fake_ctx)

    monkeypatch.setattr(employees, "WorkforceEmployeeService", _FakeEmployeeService)
    monkeypatch.setattr(employees, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(employees, "LocationService", lambda _repo: _FakeLocationService())
    monkeypatch.setattr(employees, "LocationRepo", lambda _db: object())
    monkeypatch.setattr(employees, "WorkforceEmployeeRepo", lambda _db: object())
    monkeypatch.setattr(employees, "WorkforceDepartmentRepo", lambda _db: object())
    monkeypatch.setattr(employees, "WorkforceTitleRepo", lambda _db: object())

    monkeypatch.setattr(departments, "WorkforceDepartmentService", _FakeDepartmentService)
    monkeypatch.setattr(departments, "WorkforceDepartmentRepo", lambda _db: object())
    monkeypatch.setattr(departments, "AuditRepo", _FakeAuditRepo)

    monkeypatch.setattr(titles, "WorkforceTitleService", _FakeTitleService)
    monkeypatch.setattr(titles, "WorkforceTitleRepo", lambda _db: object())
    monkeypatch.setattr(titles, "AuditRepo", _FakeAuditRepo)

    return app


def test_employee_list_redacts_salary_for_viewer(monkeypatch, workforce_modules):
    now = datetime.now(tz=timezone.utc)
    org_id = uuid.uuid4()
    _FakeEmployeeService.listed = [
        SimpleNamespace(
            id=uuid.uuid4(),
            org_id=org_id,
            created_by_user_id=uuid.uuid4(),
            employee_code="E-001",
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            phone=None,
            department_id=None,
            title_id=None,
            manager_employee_id=None,
            location_id=None,
            employment_type="FULL_TIME",
            employment_status="ACTIVE",
            start_date=date(2026, 1, 1),
            end_date=None,
            salary_type="SALARIED",
            base_salary=Decimal("120000.00"),
            hourly_rate=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    ]
    app = _build_app(monkeypatch=monkeypatch, workforce_modules=workforce_modules, role="VIEWER")
    client = TestClient(app)
    res = client.get(f"/api/v1/workforce/employees?org_id={org_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body[0]["base_salary"] is None
    assert body[0]["hourly_rate"] is None


def test_employee_create_forbidden_for_viewer(monkeypatch, workforce_modules):
    org_id = uuid.uuid4()
    _FakeEmployeeService.created = None
    app = _build_app(monkeypatch=monkeypatch, workforce_modules=workforce_modules, role="VIEWER")
    client = TestClient(app)
    res = client.post(
        "/api/v1/workforce/employees",
        json={"org_id": str(org_id), "first_name": "A", "last_name": "B"},
    )
    assert res.status_code == 403


def test_employee_create_forbidden_for_manager(monkeypatch, workforce_modules):
    org_id = uuid.uuid4()
    app = _build_app(monkeypatch=monkeypatch, workforce_modules=workforce_modules, role="MANAGER")
    client = TestClient(app)
    res = client.post(
        "/api/v1/workforce/employees",
        json={"org_id": str(org_id), "first_name": "A", "last_name": "B"},
    )
    assert res.status_code == 403


def test_department_create_allowed_for_editor(monkeypatch, workforce_modules):
    now = datetime.now(tz=timezone.utc)
    org_id = uuid.uuid4()
    _FakeDepartmentService.created = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        created_by_user_id=uuid.uuid4(),
        name="Operations",
        code="OPS",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    app = _build_app(monkeypatch=monkeypatch, workforce_modules=workforce_modules, role="EDITOR")
    client = TestClient(app)
    res = client.post(
        "/api/v1/workforce/departments",
        json={"org_id": str(org_id), "name": "Operations", "code": "OPS", "is_active": True},
    )
    assert res.status_code == 200, res.text
    assert res.json()["name"] == "Operations"


def test_workforce_endpoints_reject_cross_org(monkeypatch, workforce_modules):
    allowed_org_id = uuid.uuid4()
    blocked_org_id = uuid.uuid4()
    app = _build_isolation_app(monkeypatch=monkeypatch, workforce_modules=workforce_modules, allowed_org_id=allowed_org_id)
    client = TestClient(app)
    responses = [
        client.get(f"/api/v1/workforce/employees?org_id={blocked_org_id}"),
        client.get(f"/api/v1/workforce/departments?org_id={blocked_org_id}"),
        client.get(f"/api/v1/workforce/titles?org_id={blocked_org_id}"),
    ]
    for res in responses:
        assert res.status_code == 403
        assert res.json()["detail"] == "Forbidden"


def test_workforce_endpoints_reject_header_query_org_mismatch(monkeypatch, workforce_modules):
    allowed_org_id = uuid.uuid4()
    app = _build_isolation_app(monkeypatch=monkeypatch, workforce_modules=workforce_modules, allowed_org_id=allowed_org_id)
    client = TestClient(app)
    res = client.get(
        f"/api/v1/workforce/employees?org_id={allowed_org_id}",
        headers={"X-Org-Id": str(uuid.uuid4())},
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "org_id does not match request context"


def test_workforce_endpoints_reject_header_body_org_mismatch(monkeypatch, workforce_modules):
    now = datetime.now(tz=timezone.utc)
    allowed_org_id = uuid.uuid4()
    _FakeDepartmentService.created = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=allowed_org_id,
        created_by_user_id=uuid.uuid4(),
        name="Operations",
        code="OPS",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    app = _build_app(monkeypatch=monkeypatch, workforce_modules=workforce_modules, role="OWNER")
    client = TestClient(app)
    res = client.post(
        "/api/v1/workforce/departments",
        json={"org_id": str(allowed_org_id), "name": "Operations"},
        headers={"X-Org-Id": str(uuid.uuid4())},
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "org_id does not match request context"


def test_employee_list_filters_for_manager_scope(monkeypatch, workforce_modules):
    employees, _departments, _titles = workforce_modules
    now = datetime.now(tz=timezone.utc)
    org_id = uuid.uuid4()
    team_id = uuid.uuid4()
    other_id = uuid.uuid4()
    _FakeEmployeeService.listed = [
        SimpleNamespace(
            id=team_id,
            org_id=org_id,
            created_by_user_id=uuid.uuid4(),
            employee_code="E-TEAM",
            first_name="Team",
            last_name="Member",
            email="team@example.com",
            phone=None,
            department_id=None,
            title_id=None,
            manager_employee_id=None,
            location_id=None,
            employment_type="FULL_TIME",
            employment_status="ACTIVE",
            start_date=date(2026, 1, 1),
            end_date=None,
            salary_type="SALARIED",
            base_salary=Decimal("1000.00"),
            hourly_rate=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
        SimpleNamespace(
            id=other_id,
            org_id=org_id,
            created_by_user_id=uuid.uuid4(),
            employee_code="E-OTHER",
            first_name="Other",
            last_name="Member",
            email="other@example.com",
            phone=None,
            department_id=None,
            title_id=None,
            manager_employee_id=None,
            location_id=None,
            employment_type="FULL_TIME",
            employment_status="ACTIVE",
            start_date=date(2026, 1, 1),
            end_date=None,
            salary_type="SALARIED",
            base_salary=Decimal("2000.00"),
            hourly_rate=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        ),
    ]
    app = _build_app(monkeypatch=monkeypatch, workforce_modules=workforce_modules, role="MANAGER")
    client = TestClient(app)

    async def fake_scope(**_kwargs):
        return SimpleNamespace(
            role="MANAGER",
            can_access_employee=lambda eid: eid == team_id,
            is_manager=True,
        )

    monkeypatch.setattr(employees, "build_workforce_access_scope", fake_scope)
    res = client.get(f"/api/v1/workforce/employees?org_id={org_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body) == 1
    assert body[0]["id"] == str(team_id)
    assert body[0]["base_salary"] is None

