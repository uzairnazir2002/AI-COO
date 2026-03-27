import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domain.services.transaction_service import TransactionService


class _FakeTxRepo:
    def __init__(self):
        self.rows: list[dict] = []
        self.months: list[date] = []

    async def create(self, tx):
        self.rows.append(
            {
                "date": tx.date,
                "amount": tx.amount,
                "type": tx.type,
                "category": tx.category,
                "location_id": tx.location_id,
                "vendor": tx.vendor,
            }
        )
        return tx

    async def existing_duplicate_keys(self, org_id, txs):
        if not txs:
            return set()
        return {
            (
                existing["date"],
                existing["amount"],
                existing["type"],
                existing["category"],
                existing["location_id"],
                existing["vendor"],
            )
            for existing in self.rows
        }

    async def upsert_monthly_aggregate(self, org_id, d):
        self.months.append(d)


class _FakeAuditRepo:
    async def log(self, *args, **kwargs):
        return None


class _FakeLocationRepo:
    def __init__(self, rows):
        self.rows = rows

    async def list_by_org(self, org_id, *, include_inactive=False):
        _ = (org_id, include_inactive)
        return self.rows


@pytest.mark.asyncio
async def test_csv_import_skips_duplicates(monkeypatch):
    class _Cfg:
        csv_max_bytes = 1024 * 1024

    monkeypatch.setattr("app.domain.services.transaction_service.get_settings", lambda: _Cfg())
    repo = _FakeTxRepo()
    svc = TransactionService(repo, _FakeAuditRepo())

    content = (
        b"date,amount,type,category,vendor,notes\n"
        b"2026-02-01,100.00,EXPENSE,Ops,ACME,one\n"
        b"2026-02-01,100.00,EXPENSE,Ops,ACME,duplicate\n"
        b"2026-02-02,250.00,REVENUE,Sales,,two\n"
    )
    mapping = {
        "date": "date",
        "amount": "amount",
        "type": "type",
        "category": "category",
        "vendor": "vendor",
        "notes": "notes",
    }

    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    _, preview, inserted = await svc.import_csv(user_id, org_id, content, mapping, "sample.csv")

    assert inserted == 2
    assert preview["rows"] == 3
    assert preview["detected_duplicates"] == 1
    assert len(repo.rows) == 2
    assert repo.rows[0]["amount"] == Decimal("100.00")


@pytest.mark.asyncio
async def test_csv_import_resolves_location_mapping(monkeypatch):
    class _Cfg:
        csv_max_bytes = 1024 * 1024

    monkeypatch.setattr("app.domain.services.transaction_service.get_settings", lambda: _Cfg())
    repo = _FakeTxRepo()
    location_id = uuid.uuid4()
    location_repo = _FakeLocationRepo(
        [SimpleNamespace(id=location_id, name="Karachi HQ", code="KHI", is_active=True)]
    )
    svc = TransactionService(repo, _FakeAuditRepo(), location_repo=location_repo)

    content = (
        b"date,amount,type,category,vendor,notes,location\n"
        b"2026-02-01,100.00,EXPENSE,Ops,ACME,one,Karachi HQ\n"
        b"2026-02-02,120.00,EXPENSE,Ops,ACME,two,KHI\n"
    )
    mapping = {
        "date": "date",
        "amount": "amount",
        "type": "type",
        "category": "category",
        "vendor": "vendor",
        "notes": "notes",
        "location": "location",
    }

    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    _, _, inserted = await svc.import_csv(user_id, org_id, content, mapping, "sample.csv")

    assert inserted == 2
    assert {row["location_id"] for row in repo.rows} == {location_id}


@pytest.mark.asyncio
async def test_csv_import_fails_for_unknown_location(monkeypatch):
    class _Cfg:
        csv_max_bytes = 1024 * 1024

    monkeypatch.setattr("app.domain.services.transaction_service.get_settings", lambda: _Cfg())
    repo = _FakeTxRepo()
    location_repo = _FakeLocationRepo([])
    svc = TransactionService(repo, _FakeAuditRepo(), location_repo=location_repo)

    content = b"date,amount,type,category,location\n2026-02-01,100.00,EXPENSE,Ops,Missing Branch\n"
    mapping = {
        "date": "date",
        "amount": "amount",
        "type": "type",
        "category": "category",
        "location": "location",
    }

    with pytest.raises(ValueError, match="unknown location"):
        await svc.import_csv(uuid.uuid4(), uuid.uuid4(), content, mapping, "sample.csv")
