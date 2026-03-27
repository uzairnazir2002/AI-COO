#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import random
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed large transaction dataset for load testing.")
    p.add_argument("--org-id", action="append", help="Target organization UUID (repeatable)")
    p.add_argument(
        "--org-ids-file",
        help="Optional JSON/TXT file with organization UUIDs (JSON list or one UUID per line)",
    )
    p.add_argument("--created-by", required=True, help="User UUID for created_by")
    p.add_argument("--months", type=int, default=12, help="Number of months to span (default: 12)")
    p.add_argument("--rows", type=int, default=50000, help="Number of transactions to generate per org")
    p.add_argument("--chunk-size", type=int, default=5000, help="Insert chunk size")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    return p.parse_args()


def _rand_amount(is_expense: bool) -> Decimal:
    if is_expense:
        return Decimal(str(round(random.uniform(20, 1500), 2)))
    return Decimal(str(round(random.uniform(100, 5000), 2)))


def _load_org_ids(args: argparse.Namespace) -> list[uuid.UUID]:
    values: list[str] = []
    if args.org_id:
        values.extend(args.org_id)
    if args.org_ids_file:
        content = Path(args.org_ids_file).read_text(encoding="utf-8").strip()
        if content:
            if content.startswith("["):
                parsed = json.loads(content)
                if not isinstance(parsed, list):
                    raise ValueError("--org-ids-file JSON must be a list of UUID strings")
                values.extend(str(item) for item in parsed)
            else:
                values.extend(line.strip() for line in content.splitlines() if line.strip())
    if not values:
        raise ValueError("At least one --org-id or --org-ids-file is required")
    deduped = sorted({uuid.UUID(value) for value in values}, key=str)
    return deduped


async def main() -> None:
    args = parse_args()

    from app.db.session import SessionLocal  # noqa: E402
    from app.domain.models.transaction import Transaction  # noqa: E402
    from app.domain.repos.transaction_repo import TransactionRepo  # noqa: E402

    random.seed(args.seed)

    org_ids = _load_org_ids(args)
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

    async with SessionLocal() as db:
        repo = TransactionRepo(db)
        summary_parts: list[str] = []
        for org_id in org_ids:
            touched_days: set[date] = set()
            batch: list[Transaction] = []
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
            summary_parts.append(
                f"org_id={org_id} rows={args.rows} months={args.months} month_aggregates_recomputed={len(month_days)}"
            )

    print(f"seed_complete org_count={len(org_ids)}")
    for part in summary_parts:
        print(part)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
