import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class WorkforcePayrollPeriodCreateIn(BaseModel):
    org_id: uuid.UUID
    start_date: date
    end_date: date


class WorkforcePayrollPeriodOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    start_date: date
    end_date: date
    status: str
    approved_by_user_id: uuid.UUID | None
    approved_at: datetime | None
    paid_by_user_id: uuid.UUID | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkforcePayrollGenerateDraftIn(BaseModel):
    org_id: uuid.UUID
    payroll_period_id: uuid.UUID
    include_inactive_employees: bool = False
    overtime_multiplier: Decimal = Field(default=Decimal("1.5"), ge=Decimal("1.0"), le=Decimal("5.0"))


class WorkforcePayrollPeriodActionIn(BaseModel):
    org_id: uuid.UUID


class WorkforcePayrollEntryOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    payroll_period_id: uuid.UUID
    employee_id: uuid.UUID
    salary_type: str
    base_salary: Decimal | None
    hourly_rate: Decimal | None
    overtime_multiplier: Decimal | None
    worked_minutes: int
    overtime_minutes: int
    payable_hours: Decimal | None
    unpaid_leave_deduction: Decimal | None
    gross_pay: Decimal | None
    adjustments_total: Decimal | None
    net_pay: Decimal | None
    status: str
    is_locked: bool
    created_at: datetime
    updated_at: datetime


class WorkforcePayrollAdjustmentCreateIn(BaseModel):
    org_id: uuid.UUID
    payroll_period_id: uuid.UUID
    payroll_entry_id: uuid.UUID
    employee_id: uuid.UUID
    kind: str = Field(..., max_length=20)  # BONUS/DEDUCTION/ADVANCE/REIMBURSEMENT
    amount: Decimal
    label: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=500)


class WorkforcePayrollAdjustmentOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    payroll_period_id: uuid.UUID
    payroll_entry_id: uuid.UUID
    employee_id: uuid.UUID
    kind: str
    amount: Decimal | None
    label: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class WorkforcePayslipPreviewOut(BaseModel):
    entry: WorkforcePayrollEntryOut
    adjustments: list[WorkforcePayrollAdjustmentOut]
    period: WorkforcePayrollPeriodOut

