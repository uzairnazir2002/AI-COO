from app.utils.csv_import import parse_csv


def test_csv_preview_parse():
    content = b"date,amount,type,category,vendor,notes\n2026-03-01,100.00,EXPENSE,Ops,ACME,note"
    mapping = {
        "date": "date",
        "amount": "amount",
        "type": "type",
        "category": "category",
        "vendor": "vendor",
        "notes": "notes",
    }
    rows = parse_csv(content, mapping, 1024 * 1024)
    assert len(rows) == 1
    assert rows[0]["category"] == "Ops"


def test_csv_type_alias_income_and_cost_supported():
    content = b"date,amount,type,category\n2026-03-01,100.00,INCOME,Sales\n2026-03-02,50.00,COST,Ops"
    mapping = {"date": "date", "amount": "amount", "type": "type", "category": "category"}
    rows = parse_csv(content, mapping, 1024 * 1024)
    assert rows[0]["type"] == "REVENUE"
    assert rows[1]["type"] == "EXPENSE"


def test_csv_missing_required_mapped_column_raises():
    content = b"when,amount,type,category\n2026-03-01,100.00,EXPENSE,Ops"
    mapping = {"date": "date", "amount": "amount", "type": "type", "category": "category"}
    try:
        parse_csv(content, mapping, 1024 * 1024)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Mapped columns not found" in str(exc)


def test_csv_optional_location_mapping_is_supported():
    content = b"date,amount,type,category,location\n2026-03-01,120.00,EXPENSE,Ops,Karachi HQ"
    mapping = {
        "date": "date",
        "amount": "amount",
        "type": "type",
        "category": "category",
        "location": "location",
    }
    rows = parse_csv(content, mapping, 1024 * 1024)
    assert rows[0]["location"] == "Karachi HQ"
