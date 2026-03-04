import uuid
from datetime import date, datetime

from app.core.config import get_settings
from app.domain.models.transaction import Transaction
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.transaction_repo import TransactionRepo
from app.domain.schemas.transaction import TransactionCreateIn, TransactionUpdateIn
from app.domain.services.errors import NotFoundError
from app.utils.csv_import import parse_csv


class TransactionService:
    def __init__(self, tx_repo: TransactionRepo, audit_repo: AuditRepo):
        self.tx_repo = tx_repo
        self.audit_repo = audit_repo

    async def create(self, user_id: uuid.UUID, payload: TransactionCreateIn) -> Transaction:
        tx = Transaction(
            org_id=payload.org_id,
            date=payload.date,
            amount=payload.amount,
            type=payload.type,
            category=payload.category,
            vendor=payload.vendor,
            notes=payload.notes,
            created_by=user_id,
        )
        tx = await self.tx_repo.create(tx)
        await self.tx_repo.upsert_monthly_aggregate(payload.org_id, payload.date)
        await self.audit_repo.log(user_id, payload.org_id, "transaction.create", "transaction", str(tx.id), {})
        return tx

    async def list(self, *args, **kwargs):
        return await self.tx_repo.list(*args, **kwargs)

    async def update(self, user_id: uuid.UUID, org_id: uuid.UUID, tx_id: uuid.UUID, payload: TransactionUpdateIn):
        tx = await self.tx_repo.get_by_id_org(tx_id, org_id)
        if not tx:
            raise NotFoundError("Transaction not found")
        old_date = tx.date
        for f in ["date", "amount", "category", "vendor", "notes"]:
            v = getattr(payload, f)
            if v is not None:
                setattr(tx, f, v)
        await self.tx_repo.upsert_monthly_aggregate(org_id, old_date)
        await self.tx_repo.upsert_monthly_aggregate(org_id, tx.date)
        await self.audit_repo.log(user_id, org_id, "transaction.update", "transaction", str(tx_id), {})
        return tx

    async def delete(self, user_id: uuid.UUID, org_id: uuid.UUID, tx_id: uuid.UUID):
        tx = await self.tx_repo.get_by_id_org(tx_id, org_id)
        if not tx:
            raise NotFoundError("Transaction not found")
        d = tx.date
        await self.tx_repo.delete(tx)
        await self.tx_repo.upsert_monthly_aggregate(org_id, d)
        await self.audit_repo.log(user_id, org_id, "transaction.delete", "transaction", str(tx_id), {})

    async def _normalized_csv_rows(self, content: bytes, mapping: dict[str, str]):
        settings = get_settings()
        rows = parse_csv(content, mapping, settings.csv_max_bytes)
        normalized = []
        for r in rows:
            normalized.append(
                {
                    **r,
                    "date": datetime.strptime(r["date"], "%Y-%m-%d").date() if isinstance(r["date"], str) else r["date"],
                }
            )
        return rows, normalized

    async def preview_csv(self, org_id: uuid.UUID, content: bytes, mapping: dict[str, str]):
        rows, normalized = await self._normalized_csv_rows(content, mapping)
        existing_keys = await self.tx_repo.existing_duplicate_keys(org_id, normalized)
        dup = 0
        seen: set[tuple] = set()
        for r in normalized:
            dedupe_key = (r["date"], r["amount"], r["type"], r["category"], r["vendor"])
            if dedupe_key in seen:
                dup += 1
                continue
            seen.add(dedupe_key)
            if dedupe_key in existing_keys:
                dup += 1
        import_id = f"preview-{org_id}-{len(rows)}"
        return import_id, {"rows": len(rows), "detected_duplicates": dup}

    async def import_csv(self, user_id: uuid.UUID, org_id: uuid.UUID, content: bytes, mapping: dict[str, str]):
        rows, normalized = await self._normalized_csv_rows(content, mapping)
        existing_keys = await self.tx_repo.existing_duplicate_keys(org_id, normalized)
        dup = 0
        inserted = 0
        touched_months: set[date] = set()
        seen: set[tuple] = set()
        for r in normalized:
            dedupe_key = (r["date"], r["amount"], r["type"], r["category"], r["vendor"])
            if dedupe_key in seen:
                dup += 1
                continue
            seen.add(dedupe_key)
            if dedupe_key in existing_keys:
                dup += 1
                continue
            tx = Transaction(org_id=org_id, created_by=user_id, **r)
            await self.tx_repo.create(tx)
            touched_months.add(tx.date)
            inserted += 1
        for d in touched_months:
            await self.tx_repo.upsert_monthly_aggregate(org_id, d)
        import_id = f"imp-{org_id}-{inserted}"
        await self.audit_repo.log(
            user_id,
            org_id,
            "transaction.import_csv",
            "import",
            import_id,
            {"rows": len(rows), "duplicates": dup, "inserted": inserted},
        )
        return import_id, {"rows": len(rows), "detected_duplicates": dup}, inserted

    async def bulk_remap_category(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        from_category: str,
        to_category: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> int:
        touched_month_starts = await self.tx_repo.list_month_starts_for_category(
            org_id=org_id,
            category=from_category,
            from_date=from_date,
            to_date=to_date,
        )
        updated = await self.tx_repo.bulk_remap_category(org_id, from_category, to_category, from_date, to_date)
        for month_start in touched_month_starts:
            await self.tx_repo.upsert_monthly_aggregate(org_id, month_start)
        await self.audit_repo.log(
            user_id,
            org_id,
            "transaction.bulk_remap_category",
            "transaction",
            str(org_id),
            {"from_category": from_category, "to_category": to_category, "updated_count": updated},
        )
        return updated
