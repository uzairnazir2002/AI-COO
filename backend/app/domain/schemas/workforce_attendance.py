import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field


VALID_ATTENDANCE_STATUSES = {
    "PRESENT",
    "ABSENT",
    "LATE",
    "HALF_DAY",
    "LEAVE",
    "HOLIDAY",
    "REMOTE",
    "WEEKEND_OFF",
}


class WorkforceShiftCreateIn(BaseModel):
    org_id: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    start_time: time
    end_time: time
    grace_minutes: int = Field(default=5, ge=0, le=240)
    is_active: bool = True


class WorkforceShiftUpdateIn(BaseModel):
    org_id: uuid.UUID
    name: str | None = Field(default=None, min_length=1, max_length=120)
    start_time: time | None = None
    end_time: time | None = None
    grace_minutes: int | None = Field(default=None, ge=0, le=240)
    is_active: bool | None = None


class WorkforceShiftOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    name: str
    start_time: time
    end_time: time
    grace_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkforceShiftAssignmentCreateIn(BaseModel):
    org_id: uuid.UUID
    employee_id: uuid.UUID
    shift_id: uuid.UUID
    effective_from: date
    effective_to: date | None = None


class WorkforceShiftAssignmentOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    employee_id: uuid.UUID
    shift_id: uuid.UUID
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime


class WorkforceAttendanceClockInIn(BaseModel):
    org_id: uuid.UUID
    employee_id: uuid.UUID
    at: datetime | None = None


class WorkforceAttendanceClockOutIn(BaseModel):
    org_id: uuid.UUID
    employee_id: uuid.UUID
    at: datetime | None = None


class WorkforceAttendanceManualIn(BaseModel):
    org_id: uuid.UUID
    employee_id: uuid.UUID
    work_date: date
    status: str = Field(default="PRESENT", max_length=16)
    clock_in_at: datetime | None = None
    clock_out_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)


class WorkforceAttendanceOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    employee_id: uuid.UUID
    created_by_user_id: uuid.UUID
    work_date: date
    status: str
    source: str
    shift_id: uuid.UUID | None
    shift_assignment_id: uuid.UUID | None
    clock_in_at: datetime | None
    clock_out_at: datetime | None
    is_late: bool
    minutes_late: int
    missing_checkout: bool
    worked_minutes: int
    overtime_minutes: int
    payable_hours: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime


class WorkforceAttendanceDailyOut(BaseModel):
    org_id: uuid.UUID
    date: date
    items: list[WorkforceAttendanceOut]


class WorkforceAttendanceCalendarDayOut(BaseModel):
    date: date
    totals: dict[str, int]
    late_count: int
    missing_checkout_count: int


class WorkforceAttendanceCalendarOut(BaseModel):
    org_id: uuid.UUID
    month: str
    days: list[WorkforceAttendanceCalendarDayOut]


class WorkforceAttendanceCorrectionRequestIn(BaseModel):
    org_id: uuid.UUID
    attendance_record_id: uuid.UUID
    reason: str = Field(min_length=3, max_length=500)
    proposed_clock_in_at: datetime | None = None
    proposed_clock_out_at: datetime | None = None
    proposed_status: str | None = Field(default=None, max_length=16)


class WorkforceAttendanceCorrectionReviewIn(BaseModel):
    org_id: uuid.UUID
    status: str = Field(..., max_length=16)  # APPROVED / REJECTED
    reviewer_note: str | None = Field(default=None, max_length=500)


class WorkforceAttendanceCorrectionOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    employee_id: uuid.UUID
    attendance_record_id: uuid.UUID
    requested_by_user_id: uuid.UUID
    reviewed_by_user_id: uuid.UUID | None
    status: str
    reason: str
    proposed_clock_in_at: datetime | None
    proposed_clock_out_at: datetime | None
    proposed_status: str | None
    reviewer_note: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

