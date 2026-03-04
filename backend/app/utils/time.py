from datetime import date, datetime, timezone


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)
