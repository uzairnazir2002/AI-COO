"""Parse month-scoped query parameters for APIs that expect a calendar month."""

from __future__ import annotations

from datetime import date


def parse_period_month_query(raw: str | None) -> date | None:
    """
    Accept ISO full dates (YYYY-MM-DD) or month-only (YYYY-MM), normalized to the first day of the month.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if len(s) == 7 and s[4] == "-":
        try:
            y_str, m_str = s.split("-", 1)
            return date(int(y_str), int(m_str), 1)
        except ValueError:
            return None
    try:
        d = date.fromisoformat(s)
    except ValueError:
        return None
    return d.replace(day=1)
