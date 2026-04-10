from datetime import date

from app.domain.repos.workforce_leave_request_repo import overlap_inclusive_calendar_days


def test_overlap_inclusive_calendar_days_full_overlap():
    assert overlap_inclusive_calendar_days(date(2026, 1, 5), date(2026, 1, 7), date(2026, 1, 1), date(2026, 1, 31)) == 3


def test_overlap_inclusive_calendar_days_no_overlap():
    assert overlap_inclusive_calendar_days(date(2026, 2, 1), date(2026, 2, 3), date(2026, 1, 1), date(2026, 1, 31)) == 0
