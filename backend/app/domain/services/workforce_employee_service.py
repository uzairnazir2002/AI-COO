from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.domain.models.workforce_employee import WorkforceEmployee
from app.domain.repos.workforce_department_repo import WorkforceDepartmentRepo
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_title_repo import WorkforceTitleRepo
from app.domain.services.errors import NotFoundError


VALID_EMPLOYMENT_TYPES = {"FULL_TIME", "PART_TIME", "CONTRACTOR", "INTERN"}
VALID_EMPLOYMENT_STATUSES = {"ACTIVE", "ON_LEAVE", "OFFBOARDED", "TERMINATED"}
VALID_SALARY_TYPES = {"SALARIED", "HOURLY"}


class WorkforceEmployeeService:
    def __init__(
        self,
        *,
        employee_repo: WorkforceEmployeeRepo,
        department_repo: WorkforceDepartmentRepo,
        title_repo: WorkforceTitleRepo,
    ):
        self.employee_repo = employee_repo
        self.department_repo = department_repo
        self.title_repo = title_repo

    @staticmethod
    def _normalize_name(value: str, label: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{label} is required")
        return normalized

    @staticmethod
    def _normalize_employee_code(code: str | None) -> str | None:
        if code is None:
            return None
        normalized = code.strip().upper()
        return normalized or None

    @staticmethod
    def _normalize_email(email: str | None) -> str | None:
        if email is None:
            return None
        normalized = email.strip().lower()
        return normalized or None

    @staticmethod
    def _normalize_phone(phone: str | None) -> str | None:
        if phone is None:
            return None
        normalized = phone.strip()
        return normalized or None

    @staticmethod
    def _normalize_money(value: Decimal | None, label: str) -> Decimal | None:
        if value is None:
            return None
        out = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if out < 0:
            raise ValueError(f"{label} cannot be negative")
        return out

    @staticmethod
    def _validate_dates(start_date: date | None, end_date: date | None) -> None:
        if start_date and end_date and end_date < start_date:
            raise ValueError("End date cannot be before start date")

    async def list_employees(
        self,
        *,
        org_id: uuid.UUID,
        include_inactive: bool = False,
        q: str | None = None,
        department_id: uuid.UUID | None = None,
        title_id: uuid.UUID | None = None,
        manager_employee_id: uuid.UUID | None = None,
        employment_status: str | None = None,
        limit: int = 200,
    ) -> list[WorkforceEmployee]:
        normalized_status = employment_status.strip().upper() if isinstance(employment_status, str) else None
        if normalized_status and normalized_status not in VALID_EMPLOYMENT_STATUSES:
            raise ValueError("Unsupported employment status")
        return await self.employee_repo.list_by_org(
            org_id=org_id,
            include_inactive=include_inactive,
            q=q,
            department_id=department_id,
            title_id=title_id,
            manager_employee_id=manager_employee_id,
            employment_status=normalized_status,
            limit=limit,
        )

    async def get_employee(self, *, org_id: uuid.UUID, employee_id: uuid.UUID) -> WorkforceEmployee:
        row = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
        if row is None:
            raise NotFoundError("Employee not found")
        return row

    async def create_employee(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        employee_code: str | None,
        first_name: str,
        last_name: str,
        email: str | None,
        phone: str | None,
        department_id: uuid.UUID | None,
        title_id: uuid.UUID | None,
        manager_employee_id: uuid.UUID | None,
        location_id: uuid.UUID | None,
        employment_type: str,
        employment_status: str,
        start_date: date | None,
        end_date: date | None,
        salary_type: str,
        base_salary: Decimal | None,
        hourly_rate: Decimal | None,
        is_active: bool = True,
    ) -> WorkforceEmployee:
        normalized_code = self._normalize_employee_code(employee_code)
        normalized_first = self._normalize_name(first_name, "First name")
        normalized_last = self._normalize_name(last_name, "Last name")
        normalized_email = self._normalize_email(email)
        normalized_phone = self._normalize_phone(phone)

        normalized_emp_type = employment_type.strip().upper()
        if normalized_emp_type not in VALID_EMPLOYMENT_TYPES:
            raise ValueError("Unsupported employment type")
        normalized_emp_status = employment_status.strip().upper()
        if normalized_emp_status not in VALID_EMPLOYMENT_STATUSES:
            raise ValueError("Unsupported employment status")
        normalized_salary_type = salary_type.strip().upper()
        if normalized_salary_type not in VALID_SALARY_TYPES:
            raise ValueError("Unsupported salary type")

        self._validate_dates(start_date, end_date)

        normalized_base_salary = self._normalize_money(base_salary, "Base salary")
        normalized_hourly_rate = self._normalize_money(hourly_rate, "Hourly rate")
        if normalized_salary_type == "SALARIED":
            normalized_hourly_rate = None
        if normalized_salary_type == "HOURLY":
            normalized_base_salary = None

        if department_id is not None:
            dept = await self.department_repo.get_by_id(org_id=org_id, department_id=department_id)
            if dept is None or not dept.is_active:
                raise ValueError("Department not found")
        if title_id is not None:
            title = await self.title_repo.get_by_id(org_id=org_id, title_id=title_id)
            if title is None or not title.is_active:
                raise ValueError("Title not found")
        if manager_employee_id is not None:
            manager = await self.employee_repo.get_by_id(org_id=org_id, employee_id=manager_employee_id)
            if manager is None or not manager.is_active:
                raise ValueError("Manager not found")

        if normalized_code is not None:
            existing = await self.employee_repo.get_by_employee_code(org_id=org_id, employee_code=normalized_code)
            if existing is not None:
                raise ValueError("Employee code already exists")

        return await self.employee_repo.create(
            WorkforceEmployee(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                employee_code=normalized_code,
                first_name=normalized_first,
                last_name=normalized_last,
                email=normalized_email,
                phone=normalized_phone,
                department_id=department_id,
                title_id=title_id,
                manager_employee_id=manager_employee_id,
                location_id=location_id,
                employment_type=normalized_emp_type,
                employment_status=normalized_emp_status,
                start_date=start_date,
                end_date=end_date,
                salary_type=normalized_salary_type,
                base_salary=normalized_base_salary,
                hourly_rate=normalized_hourly_rate,
                is_active=is_active,
            )
        )

    async def update_employee(
        self,
        *,
        org_id: uuid.UUID,
        employee_id: uuid.UUID,
        fields_set: set[str],
        employee_code: str | None,
        first_name: str | None,
        last_name: str | None,
        email: str | None,
        phone: str | None,
        department_id: uuid.UUID | None,
        title_id: uuid.UUID | None,
        manager_employee_id: uuid.UUID | None,
        location_id: uuid.UUID | None,
        employment_type: str | None,
        employment_status: str | None,
        start_date: date | None,
        end_date: date | None,
        salary_type: str | None,
        base_salary: Decimal | None,
        hourly_rate: Decimal | None,
        is_active: bool | None,
    ) -> WorkforceEmployee:
        row = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
        if row is None:
            raise NotFoundError("Employee not found")

        if "employee_code" in fields_set:
            normalized_code = self._normalize_employee_code(employee_code)
            row.employee_code = normalized_code
            if normalized_code is not None:
                existing = await self.employee_repo.get_by_employee_code(
                    org_id=org_id, employee_code=normalized_code, exclude_employee_id=employee_id
                )
                if existing is not None:
                    raise ValueError("Employee code already exists")

        if "first_name" in fields_set and first_name is not None:
            row.first_name = self._normalize_name(first_name, "First name")
        if "last_name" in fields_set and last_name is not None:
            row.last_name = self._normalize_name(last_name, "Last name")
        if "email" in fields_set:
            row.email = self._normalize_email(email)
        if "phone" in fields_set:
            row.phone = self._normalize_phone(phone)

        if "employment_type" in fields_set and employment_type is not None:
            normalized_type = employment_type.strip().upper()
            if normalized_type not in VALID_EMPLOYMENT_TYPES:
                raise ValueError("Unsupported employment type")
            row.employment_type = normalized_type
        if "employment_status" in fields_set and employment_status is not None:
            normalized_status = employment_status.strip().upper()
            if normalized_status not in VALID_EMPLOYMENT_STATUSES:
                raise ValueError("Unsupported employment status")
            row.employment_status = normalized_status

        if "start_date" in fields_set:
            row.start_date = start_date
        if "end_date" in fields_set:
            row.end_date = end_date
        self._validate_dates(row.start_date, row.end_date)

        next_salary_type = row.salary_type
        if "salary_type" in fields_set and salary_type is not None:
            normalized_salary_type = salary_type.strip().upper()
            if normalized_salary_type not in VALID_SALARY_TYPES:
                raise ValueError("Unsupported salary type")
            next_salary_type = normalized_salary_type
            row.salary_type = normalized_salary_type

        if "base_salary" in fields_set:
            row.base_salary = self._normalize_money(base_salary, "Base salary")
        if "hourly_rate" in fields_set:
            row.hourly_rate = self._normalize_money(hourly_rate, "Hourly rate")
        if next_salary_type == "SALARIED":
            row.hourly_rate = None
        if next_salary_type == "HOURLY":
            row.base_salary = None

        if "department_id" in fields_set:
            if department_id is not None:
                dept = await self.department_repo.get_by_id(org_id=org_id, department_id=department_id)
                if dept is None or not dept.is_active:
                    raise ValueError("Department not found")
            row.department_id = department_id
        if "title_id" in fields_set:
            if title_id is not None:
                title = await self.title_repo.get_by_id(org_id=org_id, title_id=title_id)
                if title is None or not title.is_active:
                    raise ValueError("Title not found")
            row.title_id = title_id
        if "manager_employee_id" in fields_set:
            if manager_employee_id is not None:
                if manager_employee_id == employee_id:
                    raise ValueError("Employee cannot be their own manager")
                manager = await self.employee_repo.get_by_id(org_id=org_id, employee_id=manager_employee_id)
                if manager is None or not manager.is_active:
                    raise ValueError("Manager not found")
            row.manager_employee_id = manager_employee_id

        if "location_id" in fields_set:
            row.location_id = location_id

        if "is_active" in fields_set and is_active is not None:
            row.is_active = is_active

        return row

    async def deactivate_employee(self, *, org_id: uuid.UUID, employee_id: uuid.UUID) -> WorkforceEmployee:
        row = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
        if row is None:
            raise NotFoundError("Employee not found")
        row.is_active = False
        if row.employment_status == "ACTIVE":
            row.employment_status = "OFFBOARDED"
        return row

