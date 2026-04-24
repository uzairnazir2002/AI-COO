import uuid
from datetime import date

from pydantic import BaseModel, Field


class WorkforceDashboardIntelOut(BaseModel):
    org_id: uuid.UUID
    as_of: date

    present_today: int = 0
    absent_today: int = 0
    late_today: int = 0
    missing_checkout_today: int = 0

    pending_leave_requests: int = 0

    payroll_due_periods: int = 0
    unpaid_payroll_entries: int = 0

    contract_expiring_soon: int = 0
    probation_ending_soon: int = 0

    unacknowledged_announcements: int = 0

    top_risks: list[str] = Field(default_factory=list, max_length=10)


class WorkforceAttendanceSummaryOut(BaseModel):
    present_days: int = 0
    absent_days: int = 0
    late_incidents: int = 0
    missing_checkouts: int = 0
    total_records: int = 0


class WorkforceLeaveSummaryOut(BaseModel):
    pending_requests: int = 0
    approved_requests_overlapping: int = 0


class WorkforcePayrollSummaryOut(BaseModel):
    periods_overlapping: int = 0
    total_net_pay_in_range: str = "0.00"
    unpaid_entries_in_overlapping_periods: int = 0


class WorkforceDepartmentHeadcountOut(BaseModel):
    department_id: uuid.UUID | None = None
    department_name: str
    headcount: int = 0


class WorkforceLaborCostPeriodOut(BaseModel):
    payroll_period_id: uuid.UUID
    period_start: date
    period_end: date
    total_net_pay: str = "0.00"


class WorkforceReportsSummaryOut(BaseModel):
    org_id: uuid.UUID
    from_date: date
    to_date: date
    attendance: WorkforceAttendanceSummaryOut
    leave: WorkforceLeaveSummaryOut
    payroll: WorkforcePayrollSummaryOut
    department_headcount: list[WorkforceDepartmentHeadcountOut] = Field(default_factory=list)
    labor_cost_by_period: list[WorkforceLaborCostPeriodOut] = Field(default_factory=list)
    summary_lines: list[str] = Field(default_factory=list, max_length=20)

