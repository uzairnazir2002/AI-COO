import csv
import io
from decimal import Decimal
from decimal import InvalidOperation

from app.domain.models.enums import TransactionType


def _normalize_type(value: str) -> str:
    normalized = value.strip().upper()
    if normalized in {TransactionType.REVENUE, "INCOME"}:
        return TransactionType.REVENUE
    if normalized in {TransactionType.EXPENSE, "COST"}:
        return TransactionType.EXPENSE
    raise ValueError(f"Invalid type '{value}'")


def parse_csv(content: bytes, mapping: dict[str, str], max_bytes: int) -> list[dict]:
    if len(content) > max_bytes:
        raise ValueError("CSV too large")

    required = {"date", "amount", "type", "category"}
    missing = [k for k in required if not mapping.get(k)]
    if missing:
        raise ValueError(f"Missing mapping keys: {', '.join(sorted(missing))}")

    decoded = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise ValueError("CSV is empty or missing header row")

    available_columns = set(reader.fieldnames)
    missing_columns = [mapping[k] for k in required if mapping[k] not in available_columns]
    if missing_columns:
        raise ValueError(f"Mapped columns not found in CSV header: {', '.join(sorted(missing_columns))}")

    rows: list[dict] = []
    for index, row in enumerate(reader, start=2):
        date_value = (row.get(mapping["date"]) or "").strip()
        amount_raw = (row.get(mapping["amount"]) or "").strip()
        type_raw = (row.get(mapping["type"]) or "").strip()
        category_value = (row.get(mapping["category"]) or "").strip()

        if not date_value:
            raise ValueError(f"Row {index}: missing date")
        if not amount_raw:
            raise ValueError(f"Row {index}: missing amount")
        if not type_raw:
            raise ValueError(f"Row {index}: missing type")
        if not category_value:
            raise ValueError(f"Row {index}: missing category")

        try:
            amount_value = Decimal(amount_raw.replace(",", ""))
        except InvalidOperation as exc:
            raise ValueError(f"Row {index}: invalid amount '{amount_raw}'") from exc

        ttype = _normalize_type(type_raw)
        rows.append(
            {
                "date": date_value,
                "amount": amount_value,
                "type": ttype,
                "category": category_value,
                "vendor": row.get(mapping.get("vendor", ""), "") or None,
                "notes": row.get(mapping.get("notes", ""), "") or None,
            }
        )

    return rows
