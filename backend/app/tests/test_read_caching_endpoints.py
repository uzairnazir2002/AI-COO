from datetime import date, datetime, timezone
from importlib import reload
from types import SimpleNamespace
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app(module, prefix: str, user_id: uuid.UUID):
    app = FastAPI()
    app.include_router(module.router, prefix=prefix)

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_user():
        return SimpleNamespace(id=user_id, email="owner@example.com")

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id=None, user=None, db=None):
        _ = (org_id, user, db)
        return SimpleNamespace(org_id=org_id, role="OWNER")

    app.dependency_overrides[module.get_current_user] = fake_user
    app.dependency_overrides[module.get_db] = fake_db
    app.dependency_overrides[module.get_org_context] = fake_ctx
    module.get_org_context = fake_ctx
    return app


def test_alerts_list_uses_short_ttl_cache(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ALERTS_CACHE_TTL_SECONDS", "30")
    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.alerts as alerts_module

    alerts_module = reload(alerts_module)
    calls = {"list": 0}
    cache_store: dict[str, dict] = {}

    async def fake_cache_get(key):
        return cache_store.get(key)

    async def fake_cache_set(key, payload, _ttl):
        cache_store[key] = payload

    async def fake_cache_delete_prefix(_prefix):
        return None

    class _FakeAlertsService:
        def __init__(self, _db, _repo):
            pass

        async def list_alerts(self, _org_id, _status):
            calls["list"] += 1
            return [
                SimpleNamespace(
                    id=uuid.uuid4(),
                    kind="ANOMALY",
                    severity="HIGH",
                    title="Spike",
                    description="Detected",
                    meta={},
                    status="OPEN",
                    created_at=datetime.now(timezone.utc),
                )
            ]

    monkeypatch.setattr(alerts_module, "AlertsService", _FakeAlertsService)
    monkeypatch.setattr(alerts_module, "cache_get_json", fake_cache_get)
    monkeypatch.setattr(alerts_module, "cache_set_json", fake_cache_set)
    monkeypatch.setattr(alerts_module, "cache_delete_prefix", fake_cache_delete_prefix)

    app = _build_app(alerts_module, "/api/v1/alerts", uuid.uuid4())
    client = TestClient(app)
    org_id = uuid.uuid4()
    first = client.get(f"/api/v1/alerts?org_id={org_id}&status=OPEN")
    second = client.get(f"/api/v1/alerts?org_id={org_id}&status=OPEN")
    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["list"] == 1


def test_transactions_list_uses_short_ttl_cache(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("TRANSACTIONS_CACHE_TTL_SECONDS", "30")
    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.transactions as tx_module

    tx_module = reload(tx_module)
    calls = {"list": 0}
    cache_store: dict[str, dict] = {}

    async def fake_cache_get(key):
        return cache_store.get(key)

    async def fake_cache_set(key, payload, _ttl):
        cache_store[key] = payload

    async def fake_cache_delete_prefix(_prefix):
        return None

    class _FakeTransactionService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def list(self, *_args, **_kwargs):
            calls["list"] += 1
            return [
                SimpleNamespace(
                    id=uuid.uuid4(),
                    org_id=_args[0],
                    date=date(2026, 3, 10),
                    amount="120.00",
                    type="EXPENSE",
                    category="ops",
                    vendor="seed-load-vendor",
                    notes="seed-load",
                    created_by=uuid.uuid4(),
                    created_at=datetime.now(timezone.utc),
                )
            ], 1

    monkeypatch.setattr(tx_module, "TransactionService", _FakeTransactionService)
    monkeypatch.setattr(tx_module, "cache_get_json", fake_cache_get)
    monkeypatch.setattr(tx_module, "cache_set_json", fake_cache_set)
    monkeypatch.setattr(tx_module, "cache_delete_prefix", fake_cache_delete_prefix)

    app = _build_app(tx_module, "/api/v1/transactions", uuid.uuid4())
    client = TestClient(app)
    org_id = uuid.uuid4()
    url = f"/api/v1/transactions?org_id={org_id}&from=2026-03-01&to=2026-03-13&page=1&page_size=20&q=seed-load"
    first = client.get(url)
    second = client.get(url)
    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["list"] == 1


def test_analytics_summary_uses_short_ttl_cache(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ANALYTICS_SUMMARY_CACHE_TTL_SECONDS", "30")
    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.analytics as analytics_module

    analytics_module = reload(analytics_module)
    calls = {"summary": 0}
    cache_store: dict[str, dict] = {}

    async def fake_cache_get(key):
        return cache_store.get(key)

    async def fake_cache_set(key, payload, _ttl):
        cache_store[key] = payload

    class _FakeAnalyticsService:
        def __init__(self, _repo):
            pass

        async def summary(self, _org_id, _from_date, _to_date):
            calls["summary"] += 1
            return {
                "cash_balance": "1000.00",
                "revenue_mtd": "500.00",
                "expenses_mtd": "300.00",
                "net_profit_mtd": "200.00",
                "burn_rate_monthly": "0.00",
                "alerts_count_open": 1,
            }

    monkeypatch.setattr(analytics_module, "AnalyticsService", _FakeAnalyticsService)
    monkeypatch.setattr(analytics_module, "cache_get_json", fake_cache_get)
    monkeypatch.setattr(analytics_module, "cache_set_json", fake_cache_set)

    app = _build_app(analytics_module, "/api/v1/analytics", uuid.uuid4())
    client = TestClient(app)
    org_id = uuid.uuid4()
    url = f"/api/v1/analytics/summary?org_id={org_id}&from=2026-03-01&to=2026-03-13"
    first = client.get(url)
    second = client.get(url)
    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["summary"] == 1
