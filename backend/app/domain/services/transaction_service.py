from __future__ import annotations

import uuid
from datetime import date, datetime

from app.core.config import get_settings
from app.domain.models.transaction import Transaction
from app.domain.models.transaction_import import TransactionImport
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.import_repo import ImportRepo
from app.domain.repos.location_repo import LocationRepo
from app.domain.repos.transaction_repo import TransactionRepo
from app.domain.schemas.transaction import TransactionCreateIn, TransactionUpdateIn
from app.domain.services.errors import NotFoundError
from app.domain.services.usage_service import METRIC_TRANSACTIONS, UsageService
from app.utils.csv_import import parse_csv


class TransactionService:
    def __init__(
        self,
        tx_repo: TransactionRepo,
        audit_repo: AuditRepo,
        usage_service: UsageService | None = None,
        import_repo: ImportRepo | None = None,
        location_repo: LocationRepo | None = None,
    ):
        self.tx_repo = tx_repo
        self.audit_repo = audit_repo
        self.usage_service = usage_service
        self.import_repo = import_repo
        self.location_repo = location_repo

    async def _validate_location(self, org_id: uuid.UUID, location_id: uuid.UUID | None) -> None:
        if location_id is None or self.location_repo is None:
            return
        location = await self.location_repo.get_by_id(location_id=location_id, org_id=org_id)
        if location is None:
            raise ValueError("Location not found")
        if not location.is_active:
            raise ValueError("Location is inactive")

    @staticmethod
    def _normalize_location_key(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    async def _resolve_location_mapping(
        self,
        org_id: uuid.UUID,
        rows: list[dict],
    ) -> list[uuid.UUID | None]:
        values = [self._normalize_location_key(r.get("location")) for r in rows]
        if all(value is None for value in values):
            return [None for _ in rows]
        if self.location_repo is None:
            raise ValueError("Location mapping is not available")

        locations = await self.location_repo.list_by_org(org_id=org_id, include_inactive=True)
        by_key: dict[str, tuple[uuid.UUID, bool]] = {}
        for location in locations:
            for key in (
                self._normalize_location_key(location.name),
                self._normalize_location_key(location.code),
            ):
                if key is None:
                    continue
                by_key[key] = (location.id, bool(location.is_active))

        resolved: list[uuid.UUID | None] = []
        for idx, raw in enumerate(values, start=2):
            if raw is None:
                resolved.append(None)
                continue
            match = by_key.get(raw)
            if match is None:
                raise ValueError(f"Row {idx}: unknown location '{rows[idx - 2].get('location')}'")
            location_id, is_active = match
            if not is_active:
                raise ValueError(f"Row {idx}: location '{rows[idx - 2].get('location')}' is inactive")
            resolved.append(location_id)
        return resolved

    async def create(self, user_id: uuid.UUID, payload: TransactionCreateIn) -> Transaction:
        if self.usage_service is not None:
            await self.usage_service.consume(payload.org_id, METRIC_TRANSACTIONS, delta=1)
        tx = Transaction(
            org_id=payload.org_id,
            location_id=payload.location_id,
            date=payload.date,
            amount=payload.amount,
            type=payload.type,
            category=payload.category,
            vendor=payload.vendor,
            notes=payload.notes,
            created_by=user_id,
        )
        await self._validate_location(payload.org_id, payload.location_id)
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
        if "location_id" in payload.model_fields_set:
            await self._validate_location(org_id, payload.location_id)
            tx.location_id = payload.location_id
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

    async def _normalized_csv_rows(self, org_id: uuid.UUID, content: bytes, mapping: dict[str, str]):
        settings = get_settings()
        rows = parse_csv(content, mapping, settings.csv_max_bytes)
        resolved_locations = await self._resolve_location_mapping(org_id, rows)
        normalized = []
        for idx, r in enumerate(rows):
            normalized.append(
                {
                    **r,
                    "date": datetime.strptime(r["date"], "%Y-%m-%d").date() if isinstance(r["date"], str) else r["date"],
                    "location_id": resolved_locations[idx],
                }
            )
        return rows, normalized

    async def preview_csv(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        content: bytes,
        mapping: dict[str, str],
        file_name: str,
        mapping_profile_id: uuid.UUID | None = None,
    ):
        rows, normalized = await self._normalized_csv_rows(org_id, content, mapping)
        existing_keys = await self.tx_repo.existing_duplicate_keys(org_id, normalized)
        dup = 0
        seen: set[tuple] = set()
        error_rows: list[dict] = []
        for idx, r in enumerate(normalized, start=1):
            dedupe_key = (r["date"], r["amount"], r["type"], r["category"], r.get("location_id"), r["vendor"])
            if dedupe_key in seen or dedupe_key in existing_keys:
                dup += 1
                if len(error_rows) < 500:
                    error_rows.append({"row": idx, "reason": "duplicate", "data": {k: str(v) for k, v in r.items()}})
                continue
            seen.add(dedupe_key)

        record = await self._create_import_record(
            user_id=user_id,
            org_id=org_id,
            file_name=file_name,
            status="PREVIEW",
            total_rows=len(rows),
            inserted_count=0,
            duplicate_count=dup,
            error_rows=error_rows,
            mapping=mapping,
            mapping_profile_id=mapping_profile_id,
        )
        return str(record.id), {"rows": len(rows), "detected_duplicates": dup}

    async def import_csv(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        content: bytes,
        mapping: dict[str, str],
        file_name: str,
        mapping_profile_id: uuid.UUID | None = None,
    ):
        rows, normalized = await self._normalized_csv_rows(org_id, content, mapping)
        existing_keys = await self.tx_repo.existing_duplicate_keys(org_id, normalized)
        dup = 0
        inserted = 0
        touched_months: set[date] = set()
        seen: set[tuple] = set()
        to_insert: list[dict] = []
        error_rows: list[dict] = []

        for idx, r in enumerate(normalized, start=1):
            dedupe_key = (r["date"], r["amount"], r["type"], r["category"], r.get("location_id"), r["vendor"])
            if dedupe_key in seen:
                dup += 1
                if len(error_rows) < 500:
                    error_rows.append({"row": idx, "reason": "duplicate_in_file", "data": {k: str(v) for k, v in r.items()}})
                continue
            seen.add(dedupe_key)
            if dedupe_key in existing_keys:
                dup += 1
                if len(error_rows) < 500:
                    error_rows.append({"row": idx, "reason": "duplicate_existing", "data": {k: str(v) for k, v in r.items()}})
                continue
            to_insert.append(r)

        if self.usage_service is not None and to_insert:
            await self.usage_service.consume(org_id, METRIC_TRANSACTIONS, delta=len(to_insert))

        for r in to_insert:
            payload = {k: v for k, v in r.items() if k != "location"}
            tx = Transaction(org_id=org_id, created_by=user_id, **payload)
            await self.tx_repo.create(tx)
            touched_months.add(tx.date)
            inserted += 1

        for d in touched_months:
            await self.tx_repo.upsert_monthly_aggregate(org_id, d)

        record = await self._create_import_record(
            user_id=user_id,
            org_id=org_id,
            file_name=file_name,
            status="COMPLETED",
            total_rows=len(rows),
            inserted_count=inserted,
            duplicate_count=dup,
            error_rows=error_rows,
            mapping=mapping,
            mapping_profile_id=mapping_profile_id,
        )

        await self.audit_repo.log(
            user_id,
            org_id,
            "transaction.import_csv",
            "import",
            str(record.id),
            {"rows": len(rows), "duplicates": dup, "inserted": inserted},
        )
        return str(record.id), {"rows": len(rows), "detected_duplicates": dup}, inserted

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

    async def _create_import_record(
        self,
        *,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        file_name: str,
        status: str,
        total_rows: int,
        inserted_count: int,
        duplicate_count: int,
        error_rows: list[dict],
        mapping: dict[str, str],
        mapping_profile_id: uuid.UUID | None = None,
    ) -> TransactionImport:
        if self.import_repo is None:
            return TransactionImport(
                org_id=org_id,
                created_by=user_id,
                file_name=file_name,
                status=status,
                total_rows=total_rows,
                inserted_count=inserted_count,
                duplicate_count=duplicate_count,
                error_count=len(error_rows),
                mapping_profile_id=mapping_profile_id,
                mapping_json=mapping,
                error_rows_json=error_rows,
            )

        record = TransactionImport(
            org_id=org_id,
            created_by=user_id,
            file_name=file_name,
            status=status,
            total_rows=total_rows,
            inserted_count=inserted_count,
            duplicate_count=duplicate_count,
            error_count=len(error_rows),
            mapping_profile_id=mapping_profile_id,
            mapping_json=mapping,
            error_rows_json=error_rows,
        )
        return await self.import_repo.create(record)
