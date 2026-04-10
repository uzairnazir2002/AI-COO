from datetime import date

from app.api.period_month import parse_period_month_query


def test_parse_period_month_yyyy_mm() -> None:
    assert parse_period_month_query("2026-04") == date(2026, 4, 1)


def test_parse_period_month_yyyy_mm_dd() -> None:
    assert parse_period_month_query("2026-04-15") == date(2026, 4, 1)


def test_parse_period_month_none() -> None:
    assert parse_period_month_query(None) is None


def test_parse_period_month_invalid() -> None:
    assert parse_period_month_query("not-a-date") is None
