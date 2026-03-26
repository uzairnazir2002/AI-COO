from datetime import date
from decimal import Decimal
from importlib import reload
from types import SimpleNamespace
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app(module):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/analytics")

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


def test_location_benchmark_endpoint_returns_grouped_metrics(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.analytics as analytics_module

    analytics_module = reload(analytics_module)

    class _FakeAnalyticsService:
        def __init__(self, _repo):
            pass

        async def location_benchmark(self, org_id, from_date, to_date):
            return {
                "org_id": org_id,
                "from_date": from_date,
                "to_date": to_date,
                "totals": {
                    "revenue": Decimal("1000.00"),
                    "expense": Decimal("650.00"),
                    "net": Decimal("350.00"),
                },
                "locations": [
                    {
                        "location_id": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                        "location_name": "Karachi HQ",
                        "transaction_count": 12,
                        "revenue": Decimal("800.00"),
                        "expense": Decimal("500.00"),
                        "net": Decimal("300.00"),
                        "margin_pct": Decimal("37.50"),
                        "revenue_share_pct": Decimal("80.00"),
                        "expense_share_pct": Decimal("76.92"),
                    }
                ],
            }

    monkeypatch.setattr(analytics_module, "AnalyticsService", _FakeAnalyticsService)

    app = _build_app(analytics_module)
    client = TestClient(app)
    org_id = uuid.uuid4()

    response = client.get(
        f"/api/v1/analytics/location-benchmark?org_id={org_id}&from=2026-03-01&to=2026-03-31"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["org_id"] == str(org_id)
    assert payload["totals"]["net"] == "350.00"
    assert payload["locations"][0]["location_name"] == "Karachi HQ"
    assert payload["locations"][0]["margin_pct"] == "37.50"


def test_location_benchmark_rejects_invalid_range(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.analytics as analytics_module

    analytics_module = reload(analytics_module)
    app = _build_app(analytics_module)
    client = TestClient(app)
    org_id = uuid.uuid4()

    response = client.get(
        f"/api/v1/analytics/location-benchmark?org_id={org_id}&from=2026-03-31&to=2026-03-01"
    )
    assert response.status_code == 422
