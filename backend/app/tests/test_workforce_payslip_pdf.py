from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.domain.services.workforce_payslip_pdf import build_workforce_payslip_pdf_bytes


def test_payslip_pdf_is_valid_pdf():
    entry = SimpleNamespace(
        salary_type="SALARIED",
        base_salary=Decimal("1000.00"),
        unpaid_leave_deduction=Decimal("0"),
        hourly_rate=None,
        worked_minutes=0,
        overtime_minutes=0,
        overtime_multiplier=Decimal("1.5"),
        payable_hours=Decimal("0"),
        gross_pay=Decimal("1000.00"),
        net_pay=Decimal("1000.00"),
    )
    period = SimpleNamespace(start_date=date(2026, 1, 1), end_date=date(2026, 1, 15), status="DRAFT")
    out = build_workforce_payslip_pdf_bytes(
        employee_name="Test User",
        redact=False,
        entry=entry,
        period=period,
        adjustments=[],
    )
    assert out.startswith(b"%PDF")
