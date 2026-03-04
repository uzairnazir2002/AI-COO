from datetime import date

from app.utils.idempotency import report_key


def test_report_key_stable():
    k1 = report_key("org", date(2026, 3, 2))
    k2 = report_key("org", date(2026, 3, 2))
    assert k1 == k2
