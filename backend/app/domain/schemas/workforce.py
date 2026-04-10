import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class WorkforceDepartmentCreateIn(BaseModel):
    org_id: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    is_active: bool = True


class WorkforceDepartmentUpdateIn(BaseModel):
    org_id: uuid.UUID
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    is_active: bool | None = None


class WorkforceDepartmentOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    name: str
    code: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkforceTitleCreateIn(BaseModel):
    org_id: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    level: int | None = Field(default=None, ge=0, le=100)
    is_active: bool = True


class WorkforceTitleUpdateIn(BaseModel):
    org_id: uuid.UUID
    name: str | None = Field(default=None, min_length=1, max_length=120)
    level: int | None = Field(default=None, ge=0, le=100)
    is_active: bool | None = None


class WorkforceTitleOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    name: str
    level: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkforceEmployeeCreateIn(BaseModel):
    org_id: uuid.UUID
    employee_code: str | None = Field(default=None, min_length=1, max_length=40)
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=40)

    department_id: uuid.UUID | None = None
    title_id: uuid.UUID | None = None
    manager_employee_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None

    employment_type: str = Field(default="FULL_TIME", max_length=16)
    employment_status: str = Field(default="ACTIVE", max_length=16)
    start_date: date | None = None
    end_date: date | None = None

    salary_type: str = Field(default="SALARIED", max_length=16)
    base_salary: Decimal | None = None
    hourly_rate: Decimal | None = None

    is_active: bool = True


class WorkforceEmployeeUpdateIn(BaseModel):
    org_id: uuid.UUID
    employee_code: str | None = Field(default=None, min_length=1, max_length=40)
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=40)

    department_id: uuid.UUID | None = None
    title_id: uuid.UUID | None = None
    manager_employee_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None

    employment_type: str | None = Field(default=None, max_length=16)
    employment_status: str | None = Field(default=None, max_length=16)
    start_date: date | None = None
    end_date: date | None = None

    salary_type: str | None = Field(default=None, max_length=16)
    base_salary: Decimal | None = None
    hourly_rate: Decimal | None = None

    is_active: bool | None = None


class WorkforceEmployeeOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    employee_code: str | None
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    department_id: uuid.UUID | None
    title_id: uuid.UUID | None
    manager_employee_id: uuid.UUID | None
    location_id: uuid.UUID | None
    employment_type: str
    employment_status: str
    start_date: date | None
    end_date: date | None
    salary_type: str
    base_salary: Decimal | None
    hourly_rate: Decimal | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

