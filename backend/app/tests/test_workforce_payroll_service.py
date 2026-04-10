from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domain.services.workforce_payroll_service import WorkforcePayrollService


def _svc():
    return WorkforcePayrollService(
        payroll_repo=SimpleNamespace(),
        employee_repo=SimpleNamespace(),
        attendance_repo=SimpleNamespace(),
        leave_request_repo=SimpleNamespace(),
    )


def test_hourly_overtime_gross_pay():
    svc = _svc()
    entry = SimpleNamespace(
        salary_type="HOURLY",
        hourly_rate=Decimal("10"),
        base_salary=None,
        unpaid_leave_deduction=Decimal("0"),
        worked_minutes=600,  # 10h
        overtime_minutes=120,  # 2h overtime
        overtime_multiplier=Decimal("1.5"),
    )
    totals = svc._compute_totals(entry=entry, adjustments=[])
    # 8h * 10 + 2h * 10 * 1.5 = 80 + 30 = 110
    assert totals.gross_pay == Decimal("110.00")
    assert totals.net_pay == Decimal("110.00")


def test_salaried_gross_pay_ignores_hours():
    svc = _svc()
    entry = SimpleNamespace(
        salary_type="SALARIED",
        hourly_rate=None,
        base_salary=Decimal("2000"),
        unpaid_leave_deduction=Decimal("0"),
        worked_minutes=0,
        overtime_minutes=0,
        overtime_multiplier=Decimal("1.5"),
    )
    totals = svc._compute_totals(entry=entry, adjustments=[])
    assert totals.gross_pay == Decimal("2000.00")


def test_salaried_gross_subtracts_unpaid_leave_snapshot():
    svc = _svc()
    entry = SimpleNamespace(
        salary_type="SALARIED",
        hourly_rate=None,
        base_salary=Decimal("3000"),
        unpaid_leave_deduction=Decimal("300"),
        worked_minutes=0,
        overtime_minutes=0,
        overtime_multiplier=Decimal("1.5"),
    )
    totals = svc._compute_totals(entry=entry, adjustments=[])
    assert totals.gross_pay == Decimal("2700.00")


def test_adjustments_affect_net_pay():
    svc = _svc()
    entry = SimpleNamespace(
        salary_type="SALARIED",
        base_salary=Decimal("1000"),
        unpaid_leave_deduction=Decimal("0"),
        hourly_rate=None,
        worked_minutes=0,
        overtime_minutes=0,
        overtime_multiplier=Decimal("1.5"),
    )
    adjustments = [
        SimpleNamespace(kind="BONUS", amount=Decimal("50")),
        SimpleNamespace(kind="DEDUCTION", amount=Decimal("10")),
        SimpleNamespace(kind="ADVANCE", amount=Decimal("20")),
        SimpleNamespace(kind="REIMBURSEMENT", amount=Decimal("5")),
    ]
    totals = svc._compute_totals(entry=entry, adjustments=adjustments)
    # +50 -10 -20 +5 = +25
    assert totals.adjustments_total == Decimal("25.00")
    assert totals.net_pay == Decimal("1025.00")


def test_blank_salary_type_defaults_to_salaried():
    svc = _svc()
    entry = SimpleNamespace(
        salary_type="",
        base_salary=Decimal("1000"),
        unpaid_leave_deduction=Decimal("0"),
        hourly_rate=Decimal("10"),
        worked_minutes=480,
        overtime_minutes=0,
        overtime_multiplier=Decimal("1.5"),
    )
    totals = svc._compute_totals(entry=entry, adjustments=[])
    assert totals.gross_pay == Decimal("1000.00")


def test_unknown_salary_type_zero_gross():
    svc = _svc()
    entry = SimpleNamespace(
        salary_type="UNKNOWN",
        base_salary=Decimal("1000"),
        unpaid_leave_deduction=Decimal("0"),
        hourly_rate=Decimal("10"),
        worked_minutes=480,
        overtime_minutes=0,
        overtime_multiplier=Decimal("1.5"),
    )
    totals = svc._compute_totals(entry=entry, adjustments=[])
    assert totals.gross_pay == Decimal("0.00")

