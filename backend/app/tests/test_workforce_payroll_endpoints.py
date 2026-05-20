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


def _entry_row(*, gross_pay: Decimal = Decimal("100.00")):
    now = datetime.now(tz=timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        created_by_user_id=uuid.uuid4(),
        payroll_period_id=uuid.uuid4(),
        employee_id=uuid.uuid4(),
        salary_type="HOURLY",
        base_salary=Decimal("0"),
        hourly_rate=Decimal("25.00"),
        overtime_multiplier=Decimal("1.5"),
        worked_minutes=480,
        overtime_minutes=0,
        payable_hours=Decimal("8.00"),
        unpaid_leave_deduction=Decimal("0"),
        gross_pay=gross_pay,
        adjustments_total=Decimal("0"),
        net_pay=gross_pay,
        status="DRAFT",
        is_locked=False,
        created_at=now,
        updated_at=now,
    )


class _FakePayrollService:
    entries: list = []
    csv_text: str = "hdr\n"
    period_row: SimpleNamespace | None = None

    def __init__(self, **_kwargs):
        pass

    async def list_periods(self, **_kwargs):
        return []

    async def create_period(self, **_kwargs):
        raise AssertionError("not used")

    async def generate_draft(self, **_kwargs):
        raise AssertionError("not used")

    async def list_entries(self, **_kwargs):
        return list(type(self).entries)

    async def approve_period(self, **_kwargs):
        raise AssertionError("not used")

    async def mark_paid(self, **_kwargs):
        if type(self).period_row is None:
            raise AssertionError("period_row not set")
        return type(self).period_row

    async def export_csv(self, **_kwargs):
        return type(self).csv_text

    async def create_adjustment(self, **_kwargs):
        raise AssertionError("not used")

    async def delete_adjustment(self, **_kwargs):
        return None


@pytest.fixture
def payroll_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.workforce.payroll as payroll

    return reload(payroll)


def _build_app(*, monkeypatch, payroll_module, role="OWNER"):
    app = FastAPI()
    app.include_router(payroll_module.router, prefix="/api/v1/workforce/payroll")

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

    app.dependency_overrides[payroll_module.get_current_user] = fake_user
    app.dependency_overrides[payroll_module.get_db] = fake_db
    from app.api import deps as shared_deps
    app.dependency_overrides[shared_deps.get_db] = fake_db
    app.dependency_overrides[shared_deps.get_current_user] = fake_user
    monkeypatch.setattr(payroll_module, "get_org_context", fake_ctx)
    monkeypatch.setattr(payroll_module, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(payroll_module, "_svc", lambda _db: _FakePayrollService())

    return app


def test_payroll_create_period_forbidden_for_viewer(monkeypatch, payroll_module):
    app = _build_app(monkeypatch=monkeypatch, payroll_module=payroll_module, role="VIEWER")
    client = TestClient(app)
    oid = str(uuid.uuid4())
    res = client.post(
        "/api/v1/workforce/payroll/periods",
        json={"org_id": oid, "start_date": "2026-01-01", "end_date": "2026-01-15"},
    )
    assert res.status_code == 403


def test_payroll_create_adjustment_forbidden_for_viewer(monkeypatch, payroll_module):
    app = _build_app(monkeypatch=monkeypatch, payroll_module=payroll_module, role="VIEWER")
    client = TestClient(app)
    oid = str(uuid.uuid4())
    res = client.post(
        "/api/v1/workforce/payroll/adjustments",
        json={
            "org_id": oid,
            "payroll_period_id": str(uuid.uuid4()),
            "payroll_entry_id": str(uuid.uuid4()),
            "employee_id": str(uuid.uuid4()),
            "kind": "BONUS",
            "amount": "10.00",
        },
    )
    assert res.status_code == 403


def test_payroll_list_entries_redacts_for_viewer(monkeypatch, payroll_module):
    _FakePayrollService.entries = [_entry_row(gross_pay=Decimal("123.45"))]
    app = _build_app(monkeypatch=monkeypatch, payroll_module=payroll_module, role="VIEWER")
    client = TestClient(app)
    pid = str(uuid.uuid4())
    oid = str(uuid.uuid4())
    res = client.get(f"/api/v1/workforce/payroll/periods/{pid}/entries?org_id={oid}")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["gross_pay"] is None
    assert data[0]["net_pay"] is None
    assert data[0]["payable_hours"] is None
    assert data[0]["unpaid_leave_deduction"] is None


def test_payroll_list_entries_shows_amounts_for_editor(monkeypatch, payroll_module):
    _FakePayrollService.entries = [_entry_row(gross_pay=Decimal("123.45"))]
    app = _build_app(monkeypatch=monkeypatch, payroll_module=payroll_module, role="EDITOR")
    client = TestClient(app)
    pid = str(uuid.uuid4())
    oid = str(uuid.uuid4())
    res = client.get(f"/api/v1/workforce/payroll/periods/{pid}/entries?org_id={oid}")
    assert res.status_code == 200
    data = res.json()
    assert data[0]["gross_pay"] == "123.45"


def test_payroll_mark_paid_forbidden_for_editor(monkeypatch, payroll_module):
    app = _build_app(monkeypatch=monkeypatch, payroll_module=payroll_module, role="EDITOR")
    client = TestClient(app)
    pid = str(uuid.uuid4())
    oid = str(uuid.uuid4())
    res = client.post(f"/api/v1/workforce/payroll/periods/{pid}/mark-paid", json={"org_id": oid})
    assert res.status_code == 403


def test_payroll_mark_paid_ok_for_owner(monkeypatch, payroll_module):
    now = datetime.now(tz=timezone.utc)
    _FakePayrollService.period_row = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        created_by_user_id=uuid.uuid4(),
        start_date=now.date(),
        end_date=now.date(),
        status="PAID",
        approved_by_user_id=None,
        approved_at=None,
        paid_by_user_id=uuid.uuid4(),
        paid_at=now,
        created_at=now,
        updated_at=now,
    )
    app = _build_app(monkeypatch=monkeypatch, payroll_module=payroll_module, role="OWNER")
    client = TestClient(app)
    pid = str(_FakePayrollService.period_row.id)
    oid = str(_FakePayrollService.period_row.org_id)
    res = client.post(f"/api/v1/workforce/payroll/periods/{pid}/mark-paid", json={"org_id": oid})
    assert res.status_code == 200


def test_payroll_payslip_pdf_returns_pdf_bytes(monkeypatch, payroll_module):
    oid = uuid.uuid4()
    eid = uuid.uuid4()
    pid = uuid.uuid4()
    entry_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)

    entry = SimpleNamespace(
        id=entry_id,
        org_id=oid,
        created_by_user_id=uuid.uuid4(),
        payroll_period_id=pid,
        employee_id=eid,
        salary_type="SALARIED",
        base_salary=Decimal("1000.00"),
        unpaid_leave_deduction=Decimal("0"),
        hourly_rate=None,
        worked_minutes=0,
        overtime_minutes=0,
        overtime_multiplier=Decimal("1.5"),
        payable_hours=Decimal("0"),
        gross_pay=Decimal("1000.00"),
        adjustments_total=Decimal("0"),
        net_pay=Decimal("1000.00"),
        status="DRAFT",
        is_locked=False,
        created_at=now,
        updated_at=now,
    )
    period = SimpleNamespace(
        id=pid,
        org_id=oid,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 15),
        status="DRAFT",
    )

    class _FakePayrollRepo:
        def __init__(self, _db):
            pass

        async def get_entry(self, *, org_id, entry_id):
            _ = org_id
            assert entry.id == entry_id
            return entry

        async def get_period(self, *, org_id, period_id):
            _ = org_id
            assert period.id == period_id
            return period

        async def list_adjustments(self, **_kwargs):
            return []

    class _FakeEmployeeRepo:
        def __init__(self, _db):
            pass

        async def get_by_id(self, **_kwargs):
            return SimpleNamespace(first_name="Ada", last_name="Lovelace")

    monkeypatch.setattr(payroll_module, "WorkforcePayrollRepo", _FakePayrollRepo)
    monkeypatch.setattr(payroll_module, "WorkforceEmployeeRepo", _FakeEmployeeRepo)

    app = _build_app(monkeypatch=monkeypatch, payroll_module=payroll_module, role="EDITOR")
    client = TestClient(app)
    res = client.get(f"/api/v1/workforce/payroll/entries/{entry_id}/payslip/pdf?org_id={oid}")
    assert res.status_code == 200
    assert "application/pdf" in (res.headers.get("content-type") or "")
    assert res.content.startswith(b"%PDF")


def test_payroll_payslip_pdf_allowed_for_viewer(monkeypatch, payroll_module):
    oid = uuid.uuid4()
    eid = uuid.uuid4()
    pid = uuid.uuid4()
    entry_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)

    entry = SimpleNamespace(
        id=entry_id,
        org_id=oid,
        created_by_user_id=uuid.uuid4(),
        payroll_period_id=pid,
        employee_id=eid,
        salary_type="SALARIED",
        base_salary=Decimal("1000.00"),
        unpaid_leave_deduction=Decimal("0"),
        hourly_rate=None,
        worked_minutes=0,
        overtime_minutes=0,
        overtime_multiplier=Decimal("1.5"),
        payable_hours=Decimal("0"),
        gross_pay=Decimal("1000.00"),
        adjustments_total=Decimal("0"),
        net_pay=Decimal("1000.00"),
        status="DRAFT",
        is_locked=False,
        created_at=now,
        updated_at=now,
    )
    period = SimpleNamespace(
        id=pid,
        org_id=oid,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 15),
        status="DRAFT",
    )

    class _FakePayrollRepo:
        def __init__(self, _db):
            pass

        async def get_entry(self, *, org_id, entry_id):
            _ = org_id
            assert entry.id == entry_id
            return entry

        async def get_period(self, *, org_id, period_id):
            _ = org_id
            assert period.id == period_id
            return period

        async def list_adjustments(self, **_kwargs):
            return []

    class _FakeEmployeeRepo:
        def __init__(self, _db):
            pass

        async def get_by_id(self, **_kwargs):
            return SimpleNamespace(first_name="Ada", last_name="Lovelace")

    monkeypatch.setattr(payroll_module, "WorkforcePayrollRepo", _FakePayrollRepo)
    monkeypatch.setattr(payroll_module, "WorkforceEmployeeRepo", _FakeEmployeeRepo)

    app = _build_app(monkeypatch=monkeypatch, payroll_module=payroll_module, role="VIEWER")
    client = TestClient(app)
    res = client.get(f"/api/v1/workforce/payroll/entries/{entry_id}/payslip/pdf?org_id={oid}")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")
