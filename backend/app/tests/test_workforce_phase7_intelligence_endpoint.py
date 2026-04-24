import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps as api_deps
from app.db import session as db_session


@pytest.fixture()
def workforce_module():
    from app.api.v1.workforce import intelligence

    return intelligence


def _build_app(monkeypatch, workforce_module):
    async def _fake_get_current_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com", is_active=True)

    async def _fake_get_org_context(org_id, user, db):
        return SimpleNamespace(org_id=org_id, role="OWNER")

    class _FakeDb:
        pass

    async def _fake_get_db():
        yield _FakeDb()

    async def _fake_dashboard_intelligence(self, *, org_id, as_of):
        return {
            "org_id": str(org_id),
            "as_of": as_of.isoformat(),
            "present_today": 0,
            "absent_today": 0,
            "late_today": 0,
            "missing_checkout_today": 0,
            "pending_leave_requests": 0,
            "payroll_due_periods": 0,
            "unpaid_payroll_entries": 0,
            "contract_expiring_soon": 0,
            "probation_ending_soon": 0,
            "unacknowledged_announcements": 0,
            "top_risks": [],
        }

    async def _fake_reports_summary(self, *, org_id, from_date, to_date):
        return {
            "org_id": str(org_id),
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "attendance": {
                "present_days": 0,
                "absent_days": 0,
                "late_incidents": 0,
                "missing_checkouts": 0,
                "total_records": 0,
            },
            "leave": {"pending_requests": 0, "approved_requests_overlapping": 0},
            "payroll": {
                "periods_overlapping": 0,
                "total_net_pay_in_range": "0.00",
                "unpaid_entries_in_overlapping_periods": 0,
            },
            "department_headcount": [],
            "labor_cost_by_period": [],
            "summary_lines": ["stub line"],
        }

    monkeypatch.setattr(
        "app.domain.services.workforce_intelligence_service.WorkforceIntelligenceService.dashboard_intelligence",
        _fake_dashboard_intelligence,
    )
    monkeypatch.setattr(
        "app.domain.services.workforce_intelligence_service.WorkforceIntelligenceService.reports_summary",
        _fake_reports_summary,
    )

    app = FastAPI()
    app.include_router(workforce_module.router, prefix="/api/v1/workforce/intelligence")
    app.dependency_overrides[api_deps.get_current_user] = _fake_get_current_user
    monkeypatch.setattr(workforce_module, "get_org_context", _fake_get_org_context)
    app.dependency_overrides[db_session.get_db] = _fake_get_db
    return app


def test_workforce_intelligence_dashboard_smoke(monkeypatch, workforce_module):
    app = _build_app(monkeypatch=monkeypatch, workforce_module=workforce_module)
    client = TestClient(app)
    org_id = uuid.uuid4()
    res = client.get(f"/api/v1/workforce/intelligence/dashboard?org_id={org_id}&as_of={date(2026,4,1).isoformat()}")
    assert res.status_code == 200
    body = res.json()
    assert body["org_id"] == str(org_id)
    assert body["as_of"] == "2026-04-01"
    assert "top_risks" in body


def test_workforce_intelligence_reports_summary_smoke(monkeypatch, workforce_module):
    app = _build_app(monkeypatch=monkeypatch, workforce_module=workforce_module)
    client = TestClient(app)
    org_id = uuid.uuid4()
    res = client.get(
        f"/api/v1/workforce/intelligence/reports/summary?org_id={org_id}"
        f"&from={date(2026, 4, 1).isoformat()}&to={date(2026, 4, 30).isoformat()}"
    )
    assert res.status_code == 200
    body = res.json()
    assert body["org_id"] == str(org_id)
    assert body["from_date"] == "2026-04-01"
    assert body["to_date"] == "2026-04-30"
    assert body["summary_lines"] == ["stub line"]

