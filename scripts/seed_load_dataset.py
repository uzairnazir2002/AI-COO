#!/usr/bin/env python
from __future__ import annotations

import argparse
import random
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.domain.models.transaction import Transaction  # noqa: E402
from app.domain.repos.transaction_repo import TransactionRepo  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed large transaction dataset for load testing.")
    p.add_argument("--org-id", required=True, help="Target organization UUID")
    p.add_argument("--created-by", required=True, help="User UUID for created_by")
    p.add_argument("--months", type=int, default=12, help="Number of months to span (default: 12)")
    p.add_argument("--rows", type=int, default=50000, help="Number of transactions to generate")
    p.add_argument("--chunk-size", type=int, default=5000, help="Insert chunk size")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    return p.parse_args()


def _rand_amount(is_expense: bool) -> Decimal:
    if is_expense:
        return Decimal(str(round(random.uniform(20, 1500), 2)))
    return Decimal(str(round(random.uniform(100, 5000), 2)))


async def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    org_id = uuid.UUID(args.org_id)
    created_by = uuid.UUID(args.created_by)
    today = date.today()
    start = date(today.year, today.month, 1) - timedelta(days=30 * args.months)
    total_days = max(1, (today - start).days)

    revenue_categories = ["Sales", "Services", "Consulting"]
    expense_categories = ["Payroll", "Rent", "Marketing", "Software", "Misc", "Subscriptions"]
    vendors = [
        "ACME Cloud",
        "Northwind Rent",
        "Payrollly",
        "AdSpark",
        "OfficeMart",
        "LogiTrans",
        None,
    ]

    touched_days: set[date] = set()
    batch: list[Transaction] = []

    async with SessionLocal() as db:
        repo = TransactionRepo(db)
        for i in range(args.rows):
            tx_date = start + timedelta(days=random.randint(0, total_days))
            is_expense = random.random() < 0.62
            tx_type = "EXPENSE" if is_expense else "REVENUE"
            category = random.choice(expense_categories if is_expense else revenue_categories)
            vendor = random.choice(vendors if is_expense else [None, "Enterprise Client", "Retail Channel"])
            amount = _rand_amount(is_expense)

            batch.append(
                Transaction(
                    org_id=org_id,
                    date=tx_date,
                    amount=amount,
                    type=tx_type,
                    category=category,
                    vendor=vendor,
                    notes=f"seed-load-{i}",
                    created_by=created_by,
                )
            )
            touched_days.add(tx_date)

            if len(batch) >= args.chunk_size:
                db.add_all(batch)
                await db.flush()
                await db.commit()
                batch = []

        if batch:
            db.add_all(batch)
            await db.flush()
            await db.commit()

        month_days = sorted({date(d.year, d.month, 1) for d in touched_days})
        for month_day in month_days:
            await repo.upsert_monthly_aggregate(org_id, month_day)
        await db.commit()

    print(
        f"seeded org_id={org_id} rows={args.rows} months={args.months} "
        f"month_aggregates_recomputed={len(month_days)}"
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
