from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import uuid

import pytest

from app.domain.repos.inventory_repo import InventoryRepo


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalarResult(self._rows)


class _FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.added = []

    async def execute(self, _query):
        return _FakeExecuteResult(self.rows)

    def add(self, row):
        self.added.append(row)

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_get_stock_level_tolerates_duplicate_rows():
    org_id = uuid.uuid4()
    item_id = uuid.uuid4()
    rows = [
        SimpleNamespace(id=uuid.uuid4(), on_hand_qty=Decimal("10"), updated_at=datetime.now(tz=timezone.utc)),
        SimpleNamespace(id=uuid.uuid4(), on_hand_qty=Decimal("12"), updated_at=datetime.now(tz=timezone.utc)),
    ]
    repo = InventoryRepo(_FakeSession(rows))

    out = await repo.get_stock_level(org_id=org_id, item_id=item_id, location_id=None)

    assert out is rows[0]


@pytest.mark.asyncio
async def test_upsert_sales_velocity_tolerates_duplicate_rows():
    org_id = uuid.uuid4()
    item_id = uuid.uuid4()
    existing = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        item_id=item_id,
        location_id=None,
        window_days=30,
        units_per_day=Decimal("0.1000"),
        basis_start=date(2026, 2, 1),
        basis_end=date(2026, 2, 28),
    )
    duplicate = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        item_id=item_id,
        location_id=None,
        window_days=30,
        units_per_day=Decimal("0.2000"),
        basis_start=date(2026, 2, 1),
        basis_end=date(2026, 2, 28),
    )
    db = _FakeSession([existing, duplicate])
    repo = InventoryRepo(db)

    row = await repo.upsert_sales_velocity(
        org_id=org_id,
        item_id=item_id,
        location_id=None,
        window_days=30,
        units_per_day=Decimal("0.3333"),
        basis_start=date(2026, 3, 1),
        basis_end=date(2026, 3, 31),
    )

    assert row is existing
    assert row.units_per_day == Decimal("0.3333")
    assert row.basis_start == date(2026, 3, 1)
    assert row.basis_end == date(2026, 3, 31)
