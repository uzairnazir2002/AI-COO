from datetime import datetime, timezone
from decimal import Decimal
from importlib import reload
from types import SimpleNamespace
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeInventoryService:
    items: list[SimpleNamespace] = []
    created_item: SimpleNamespace | None = None
    created_event: tuple[SimpleNamespace, Decimal] | None = None
    created_po: SimpleNamespace | None = None
    forecast_payload: dict | None = None

    def __init__(self, _repo):
        pass

    async def list_items(self, **_kwargs):
        return type(self).items

    async def create_item(self, **_kwargs):
        assert type(self).created_item is not None
        return type(self).created_item

    async def record_stock_event(self, **_kwargs):
        assert type(self).created_event is not None
        return type(self).created_event

    async def create_purchase_order(self, **_kwargs):
        assert type(self).created_po is not None
        return type(self).created_po

    async def forecast(self, **_kwargs):
        assert type(self).forecast_payload is not None
        return type(self).forecast_payload


class _FakeAuditRepo:
    def __init__(self, _db):
        pass

    async def log(self, *_args, **_kwargs):
        return None


class _FakeLocationService:
    def __init__(self, _repo):
        pass

    async def ensure_org_location(self, **_kwargs):
        return None


class _FakeDb:
    async def commit(self):
        return None


class _FakeAlertRefreshService:
    def __init__(self, _repo):
        pass

    async def enqueue_recalc(self, **_kwargs):
        return SimpleNamespace(task_id="recalc-alerts-job", status="PENDING", enqueued=True)


class _FakeNotificationService:
    def __init__(self, _repo):
        pass

    async def create_org_notification(self, **_kwargs):
        return None


@pytest.fixture
def inventory_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.inventory as inventory

    return reload(inventory)


def _app(monkeypatch, module, role="OWNER"):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/inventory")
    user = SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")

    async def fake_user():
        return user

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        _ = (user, db)
        return SimpleNamespace(org_id=org_id, role=role)

    app.dependency_overrides[module.get_current_user] = fake_user
    app.dependency_overrides[module.get_db] = fake_db
    from app.api import deps as shared_deps

    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    monkeypatch.setattr(module, "get_org_context", fake_ctx)
    monkeypatch.setattr(module, "InventoryService", _FakeInventoryService)
    monkeypatch.setattr(module, "InventoryRepo", lambda _db: object())
    monkeypatch.setattr(module, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(module, "LocationService", _FakeLocationService)
    monkeypatch.setattr(module, "LocationRepo", lambda _db: object())
    monkeypatch.setattr(module, "AlertRefreshService", _FakeAlertRefreshService)
    monkeypatch.setattr(module, "JobRepo", lambda _db: object())
    monkeypatch.setattr(module, "NotificationService", _FakeNotificationService)
    monkeypatch.setattr(module, "NotificationRepo", lambda _db: object())
    return app


def test_inventory_list_and_forecast(monkeypatch, inventory_module):
    org_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    _FakeInventoryService.items = [
        SimpleNamespace(
            id=uuid.uuid4(),
            org_id=org_id,
            location_id=None,
            created_by_user_id=uuid.uuid4(),
            sku="SKU-001",
            name="Widget A",
            unit_cost=Decimal("2.50"),
            reorder_point=Decimal("10.000"),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    ]
    _FakeInventoryService.forecast_payload = {
        "generated_at": now,
        "lookback_days": 30,
        "horizon_days": 30,
        "high_risk_items": 0,
        "items": [
            {
                "item_id": str(_FakeInventoryService.items[0].id),
                "sku": "SKU-001",
                "name": "Widget A",
                "location_id": None,
                "on_hand_qty": "20.000",
                "inbound_open_qty": "0.000",
                "units_per_day": "0.1000",
                "days_of_cover": "200.0",
                "projected_stockout_date": None,
                "risk_level": "LOW",
                "reorder_point": "10.000",
                "cogs_exposure_30d": "7.50",
            }
        ],
    }
    app = _app(monkeypatch, inventory_module, role="OWNER")
    client = TestClient(app)

    listed = client.get(f"/api/v1/inventory/items?org_id={org_id}")
    assert listed.status_code == 200, listed.text
    assert len(listed.json()) == 1
    assert listed.json()[0]["sku"] == "SKU-001"

    forecast = client.get(f"/api/v1/inventory/forecast?org_id={org_id}&lookback_days=30&horizon_days=30")
    assert forecast.status_code == 200, forecast.text
    body = forecast.json()
    assert body["high_risk_items"] == 0
    assert body["items"][0]["risk_level"] == "LOW"


def test_inventory_mutations_forbidden_for_viewer(monkeypatch, inventory_module):
    org_id = uuid.uuid4()
    _FakeInventoryService.created_item = None
    app = _app(monkeypatch, inventory_module, role="VIEWER")
    client = TestClient(app)

    create = client.post(
        "/api/v1/inventory/items",
        json={
            "org_id": str(org_id),
            "sku": "SKU-002",
            "name": "Widget B",
            "unit_cost": "4.00",
            "reorder_point": "8.000",
        },
    )
    assert create.status_code == 403


def test_inventory_create_item_sets_alert_refresh_headers(monkeypatch, inventory_module):
    org_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    _FakeInventoryService.created_item = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        location_id=None,
        created_by_user_id=uuid.uuid4(),
        sku="SKU-003",
        name="Widget C",
        unit_cost=Decimal("4.00"),
        reorder_point=Decimal("6.000"),
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    app = _app(monkeypatch, inventory_module, role="OWNER")
    client = TestClient(app)
    res = client.post(
        "/api/v1/inventory/items",
        json={
            "org_id": str(org_id),
            "sku": "SKU-003",
            "name": "Widget C",
            "unit_cost": "4.00",
            "reorder_point": "6.000",
        },
    )
    assert res.status_code == 200, res.text
    assert res.headers["X-Alert-Recalc-Task-Id"] == "recalc-alerts-job"
    assert res.headers["X-Alert-Recalc-Queued"] == "true"
