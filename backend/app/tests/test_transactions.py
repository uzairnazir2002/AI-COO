from datetime import date
from decimal import Decimal

from app.domain.schemas.transaction import TransactionCreateIn


def test_transaction_schema_accepts_decimal():
    payload = TransactionCreateIn(
        org_id="d7f8ad50-a95e-4d84-a7b1-71580a4ca53a",
        date=date(2026, 3, 1),
        amount=Decimal("120.10"),
        type="EXPENSE",
        category="Ops",
    )
    assert payload.amount == Decimal("120.10")
