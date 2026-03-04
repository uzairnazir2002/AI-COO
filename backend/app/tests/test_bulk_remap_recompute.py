import uuid
from datetime import date

import pytest

from app.domain.services.transaction_service import TransactionService


class _FakeTxRepo:
    def __init__(self):
        self.upserts: list[date] = []

    async def list_month_starts_for_category(self, org_id, category, from_date=None, to_date=None):
        return [date(2025, 12, 1), date(2026, 1, 1)]

    async def bulk_remap_category(self, org_id, from_category, to_category, from_date=None, to_date=None):
        return 7

    async def upsert_monthly_aggregate(self, org_id, d):
        self.upserts.append(d)


class _FakeAuditRepo:
    async def log(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_bulk_remap_recomputes_all_touched_months():
    repo = _FakeTxRepo()
    svc = TransactionService(repo, _FakeAuditRepo())

    updated = await svc.bulk_remap_category(
        user_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        from_category="Ops",
        to_category="Operations",
    )

    assert updated == 7
    assert repo.upserts == [date(2025, 12, 1), date(2026, 1, 1)]
