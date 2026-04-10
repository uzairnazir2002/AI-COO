import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class WorkforceLeaveTypeCreateIn(BaseModel):
    org_id: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=40)
    is_paid: bool = True
    requires_approval: bool = True
    is_active: bool = True


class WorkforceLeaveTypeUpdateIn(BaseModel):
    org_id: uuid.UUID
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=40)
    is_paid: bool | None = None
    requires_approval: bool | None = None
    is_active: bool | None = None


class WorkforceLeaveTypeOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    name: str
    code: str | None
    is_paid: bool
    requires_approval: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkforceLeaveBalanceOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    employee_id: uuid.UUID
    leave_type_id: uuid.UUID
    year: int
    allocated_days: Decimal
    used_days: Decimal
    pending_days: Decimal
    created_at: datetime
    updated_at: datetime


class WorkforceLeaveBalanceAllocateIn(BaseModel):
    org_id: uuid.UUID
    employee_id: uuid.UUID
    leave_type_id: uuid.UUID
    year: int = Field(..., ge=2000, le=2100)
    allocated_days: Decimal = Field(..., ge=0)


class WorkforceLeaveRequestCreateIn(BaseModel):
    org_id: uuid.UUID
    employee_id: uuid.UUID
    leave_type_id: uuid.UUID
    start_date: date
    end_date: date
    days: Decimal = Field(default=Decimal("1"), ge=Decimal("0.5"))
    reason: str | None = Field(default=None, max_length=500)


class WorkforceLeaveRequestOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    employee_id: uuid.UUID
    leave_type_id: uuid.UUID
    start_date: date
    end_date: date
    days: Decimal
    status: str
    reason: str | None
    reviewed_by_user_id: uuid.UUID | None
    reviewed_at: datetime | None
    reviewer_note: str | None
    created_at: datetime
    updated_at: datetime


class WorkforceLeaveRequestDecisionIn(BaseModel):
    org_id: uuid.UUID
    status: str = Field(..., max_length=16)  # APPROVED / REJECTED / CANCELLED
    reviewer_note: str | None = Field(default=None, max_length=500)

