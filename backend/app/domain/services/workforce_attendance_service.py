from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from app.domain.models.workforce_attendance_correction import WorkforceAttendanceCorrection
from app.domain.models.workforce_attendance_record import WorkforceAttendanceRecord
from app.domain.repos.workforce_attendance_repo import WorkforceAttendanceRepo
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_shift_repo import WorkforceShiftRepo
from app.domain.services.errors import NotFoundError


VALID_STATUSES = {
    "PRESENT",
    "ABSENT",
    "LATE",
    "HALF_DAY",
    "LEAVE",
    "HOLIDAY",
    "REMOTE",
    "WEEKEND_OFF",
}


@dataclass
class AttendanceDerived:
    status: str
    is_late: bool
    minutes_late: int
    missing_checkout: bool
    worked_minutes: int
    overtime_minutes: int
    payable_hours: Decimal


class WorkforceAttendanceService:
    def __init__(
        self,
        *,
        attendance_repo: WorkforceAttendanceRepo,
        employee_repo: WorkforceEmployeeRepo,
        shift_repo: WorkforceShiftRepo,
    ):
        self.attendance_repo = attendance_repo
        self.employee_repo = employee_repo
        self.shift_repo = shift_repo

    @staticmethod
    def _work_date_for(at: datetime) -> date:
        return at.astimezone(timezone.utc).date()

    @staticmethod
    def _normalize_status(status: str) -> str:
        normalized = status.strip().upper()
        if normalized not in VALID_STATUSES:
            raise ValueError("Unsupported attendance status")
        return normalized

    @staticmethod
    def _quantize_hours(minutes: int) -> Decimal:
        hours = Decimal(minutes) / Decimal(60)
        return hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def _resolve_shift_for_date(
        self, *, org_id: uuid.UUID, employee_id: uuid.UUID, work_date: date
    ) -> tuple[uuid.UUID | None, uuid.UUID | None, time | None, time | None, int]:
        assignments = await self.shift_repo.list_assignments(
            org_id=org_id, employee_id=employee_id, as_of=work_date, limit=5
        )
        assignment = assignments[0] if assignments else None
        if not assignment:
            return None, None, None, None, 5
        shift = await self.shift_repo.get_shift(org_id=org_id, shift_id=assignment.shift_id)
        if shift is None or not shift.is_active:
            return None, None, None, None, 5
        return shift.id, assignment.id, shift.start_time, shift.end_time, int(shift.grace_minutes or 0)

    def _derive(self, *, status: str, clock_in_at: datetime | None, clock_out_at: datetime | None, expected_start: datetime | None, grace_minutes: int) -> AttendanceDerived:
        normalized_status = self._normalize_status(status)

        is_late = False
        minutes_late = 0
        if clock_in_at and expected_start:
            late_by = int((clock_in_at - expected_start).total_seconds() // 60)
            if late_by > max(0, int(grace_minutes)):
                is_late = True
                minutes_late = late_by

        missing_checkout = bool(clock_in_at and not clock_out_at)

        worked_minutes = 0
        if clock_in_at and clock_out_at and clock_out_at > clock_in_at:
            worked_minutes = int((clock_out_at - clock_in_at).total_seconds() // 60)

        overtime_minutes = max(0, worked_minutes - 8 * 60) if normalized_status in {"PRESENT", "LATE", "REMOTE"} else 0
        payable_hours = self._quantize_hours(worked_minutes) if worked_minutes > 0 else Decimal("0")

        # If we detected lateness, normalize to LATE unless a stronger explicit status is set.
        if is_late and normalized_status in {"PRESENT"}:
            normalized_status = "LATE"

        return AttendanceDerived(
            status=normalized_status,
            is_late=is_late,
            minutes_late=minutes_late,
            missing_checkout=missing_checkout,
            worked_minutes=worked_minutes,
            overtime_minutes=overtime_minutes,
            payable_hours=payable_hours,
        )

    async def clock_in(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        employee_id: uuid.UUID,
        at: datetime | None = None,
    ) -> WorkforceAttendanceRecord:
        emp = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
        if emp is None or not emp.is_active:
            raise ValueError("Employee not found")
        ts = (at or datetime.now(tz=timezone.utc)).astimezone(timezone.utc)
        work_date = self._work_date_for(ts)
        shift_id, assignment_id, start_time, _end_time, grace = await self._resolve_shift_for_date(
            org_id=org_id, employee_id=employee_id, work_date=work_date
        )
        expected_start = None
        if start_time is not None:
            expected_start = datetime.combine(work_date, start_time, tzinfo=timezone.utc)
        row = await self.attendance_repo.get_record_for_date(org_id=org_id, employee_id=employee_id, work_date=work_date)
        if row is None:
            row = WorkforceAttendanceRecord(
                org_id=org_id,
                employee_id=employee_id,
                created_by_user_id=actor_user_id,
                work_date=work_date,
                status="PRESENT",
                source="CLOCK",
                shift_id=shift_id,
                shift_assignment_id=assignment_id,
                clock_in_at=ts,
            )
        else:
            if row.clock_in_at is None or ts < row.clock_in_at:
                row.clock_in_at = ts
            row.source = "CLOCK"
            if shift_id:
                row.shift_id = shift_id
                row.shift_assignment_id = assignment_id
        derived = self._derive(
            status=row.status,
            clock_in_at=row.clock_in_at,
            clock_out_at=row.clock_out_at,
            expected_start=expected_start,
            grace_minutes=grace,
        )
        row.status = derived.status
        row.is_late = derived.is_late
        row.minutes_late = derived.minutes_late
        row.missing_checkout = derived.missing_checkout
        row.worked_minutes = derived.worked_minutes
        row.overtime_minutes = derived.overtime_minutes
        row.payable_hours = derived.payable_hours
        return await self.attendance_repo.upsert_record(row)

    async def clock_out(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        employee_id: uuid.UUID,
        at: datetime | None = None,
    ) -> WorkforceAttendanceRecord:
        emp = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
        if emp is None or not emp.is_active:
            raise ValueError("Employee not found")
        ts = (at or datetime.now(tz=timezone.utc)).astimezone(timezone.utc)
        work_date = self._work_date_for(ts)
        row = await self.attendance_repo.get_record_for_date(org_id=org_id, employee_id=employee_id, work_date=work_date)
        if row is None or row.clock_in_at is None:
            raise ValueError("Cannot clock out without a clock-in for this date")
        if row.clock_out_at is None or ts > row.clock_out_at:
            row.clock_out_at = ts
        row.source = "CLOCK"
        shift_id, assignment_id, start_time, _end_time, grace = await self._resolve_shift_for_date(
            org_id=org_id, employee_id=employee_id, work_date=work_date
        )
        expected_start = datetime.combine(work_date, start_time, tzinfo=timezone.utc) if start_time else None
        if shift_id:
            row.shift_id = shift_id
            row.shift_assignment_id = assignment_id
        derived = self._derive(
            status=row.status,
            clock_in_at=row.clock_in_at,
            clock_out_at=row.clock_out_at,
            expected_start=expected_start,
            grace_minutes=grace,
        )
        row.status = derived.status
        row.is_late = derived.is_late
        row.minutes_late = derived.minutes_late
        row.missing_checkout = derived.missing_checkout
        row.worked_minutes = derived.worked_minutes
        row.overtime_minutes = derived.overtime_minutes
        row.payable_hours = derived.payable_hours
        row.created_by_user_id = actor_user_id
        return await self.attendance_repo.upsert_record(row)

    async def manual_entry(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        employee_id: uuid.UUID,
        work_date: date,
        status: str,
        clock_in_at: datetime | None,
        clock_out_at: datetime | None,
        notes: str | None,
    ) -> WorkforceAttendanceRecord:
        emp = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
        if emp is None or not emp.is_active:
            raise ValueError("Employee not found")
        normalized_status = self._normalize_status(status)
        if clock_in_at is not None:
            clock_in_at = clock_in_at.astimezone(timezone.utc)
        if clock_out_at is not None:
            clock_out_at = clock_out_at.astimezone(timezone.utc)
        if clock_in_at and clock_out_at and clock_out_at < clock_in_at:
            raise ValueError("clock_out_at cannot be before clock_in_at")
        shift_id, assignment_id, start_time, _end_time, grace = await self._resolve_shift_for_date(
            org_id=org_id, employee_id=employee_id, work_date=work_date
        )
        expected_start = datetime.combine(work_date, start_time, tzinfo=timezone.utc) if start_time else None
        row = await self.attendance_repo.get_record_for_date(org_id=org_id, employee_id=employee_id, work_date=work_date)
        if row is None:
            row = WorkforceAttendanceRecord(
                org_id=org_id,
                employee_id=employee_id,
                created_by_user_id=actor_user_id,
                work_date=work_date,
            )
        row.status = normalized_status
        row.source = "MANUAL"
        row.shift_id = shift_id
        row.shift_assignment_id = assignment_id
        row.clock_in_at = clock_in_at
        row.clock_out_at = clock_out_at
        row.notes = notes.strip() if isinstance(notes, str) and notes.strip() else None
        derived = self._derive(
            status=row.status,
            clock_in_at=row.clock_in_at,
            clock_out_at=row.clock_out_at,
            expected_start=expected_start,
            grace_minutes=grace,
        )
        row.status = derived.status
        row.is_late = derived.is_late
        row.minutes_late = derived.minutes_late
        row.missing_checkout = derived.missing_checkout
        row.worked_minutes = derived.worked_minutes
        row.overtime_minutes = derived.overtime_minutes
        row.payable_hours = derived.payable_hours
        return await self.attendance_repo.upsert_record(row)

    async def daily_view(
        self, *, org_id: uuid.UUID, day: date, employee_id: uuid.UUID | None = None
    ) -> list[WorkforceAttendanceRecord]:
        return await self.attendance_repo.list_records(
            org_id=org_id, from_date=day, to_date=day, employee_id=employee_id, limit=5000
        )

    async def calendar_month(self, *, org_id: uuid.UUID, month: str) -> dict:
        # month = YYYY-MM
        try:
            year = int(month.split("-")[0])
            mon = int(month.split("-")[1])
        except Exception as exc:
            raise ValueError("month must be YYYY-MM") from exc
        if mon < 1 or mon > 12:
            raise ValueError("month must be YYYY-MM")
        start = date(year, mon, 1)
        end = date(year + (1 if mon == 12 else 0), 1 if mon == 12 else mon + 1, 1) - timedelta(days=1)
        rows = await self.attendance_repo.calendar_counts(org_id=org_id, from_date=start, to_date=end)
        by_day: dict[date, dict] = {}
        for row in rows:
            d = row["day"]
            if d not in by_day:
                by_day[d] = {"totals": defaultdict(int), "late_count": 0, "missing_checkout_count": 0}
            by_day[d]["totals"][row["status"]] += int(row["count"])
            by_day[d]["late_count"] = max(by_day[d]["late_count"], int(row["late_count"]))
            by_day[d]["missing_checkout_count"] = max(by_day[d]["missing_checkout_count"], int(row["missing_checkout_count"]))
        days = []
        cursor = start
        while cursor <= end:
            payload = by_day.get(cursor) or {"totals": {}, "late_count": 0, "missing_checkout_count": 0}
            days.append(
                {
                    "date": cursor,
                    "totals": dict(payload["totals"]),
                    "late_count": int(payload["late_count"]),
                    "missing_checkout_count": int(payload["missing_checkout_count"]),
                }
            )
            cursor = cursor + timedelta(days=1)
        return {"org_id": org_id, "month": month, "days": days}

    async def request_correction(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        attendance_record_id: uuid.UUID,
        reason: str,
        proposed_clock_in_at: datetime | None,
        proposed_clock_out_at: datetime | None,
        proposed_status: str | None,
    ) -> WorkforceAttendanceCorrection:
        record = await self.attendance_repo.get_record(org_id=org_id, record_id=attendance_record_id)
        if record is None:
            raise NotFoundError("Attendance record not found")
        if proposed_status is not None:
            proposed_status = self._normalize_status(proposed_status)
        if proposed_clock_in_at is not None:
            proposed_clock_in_at = proposed_clock_in_at.astimezone(timezone.utc)
        if proposed_clock_out_at is not None:
            proposed_clock_out_at = proposed_clock_out_at.astimezone(timezone.utc)
        if proposed_clock_in_at and proposed_clock_out_at and proposed_clock_out_at < proposed_clock_in_at:
            raise ValueError("proposed_clock_out_at cannot be before proposed_clock_in_at")
        normalized_reason = reason.strip()
        if len(normalized_reason) < 3:
            raise ValueError("Reason is required")
        return await self.attendance_repo.create_correction(
            WorkforceAttendanceCorrection(
                org_id=org_id,
                employee_id=record.employee_id,
                attendance_record_id=record.id,
                requested_by_user_id=actor_user_id,
                status="PENDING",
                reason=normalized_reason,
                proposed_clock_in_at=proposed_clock_in_at,
                proposed_clock_out_at=proposed_clock_out_at,
                proposed_status=proposed_status,
            )
        )

    async def review_correction(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        correction_id: uuid.UUID,
        status: str,
        reviewer_note: str | None,
    ) -> WorkforceAttendanceCorrection:
        corr = await self.attendance_repo.get_correction(org_id=org_id, correction_id=correction_id)
        if corr is None:
            raise NotFoundError("Correction not found")
        normalized = status.strip().upper()
        if normalized not in {"APPROVED", "REJECTED"}:
            raise ValueError("status must be APPROVED or REJECTED")
        if corr.status != "PENDING":
            raise ValueError("Correction is already reviewed")
        corr.status = normalized
        corr.reviewed_by_user_id = actor_user_id
        corr.reviewed_at = datetime.now(tz=timezone.utc)
        corr.reviewer_note = reviewer_note.strip() if isinstance(reviewer_note, str) and reviewer_note.strip() else None
        if normalized == "APPROVED":
            record = await self.attendance_repo.get_record(org_id=org_id, record_id=corr.attendance_record_id)
            if record is None:
                raise NotFoundError("Attendance record not found")
            # apply proposed changes as manual adjustments
            record.source = "MANUAL"
            if corr.proposed_clock_in_at is not None:
                record.clock_in_at = corr.proposed_clock_in_at
            if corr.proposed_clock_out_at is not None:
                record.clock_out_at = corr.proposed_clock_out_at
            if corr.proposed_status is not None:
                record.status = corr.proposed_status
            shift_id, assignment_id, start_time, _end_time, grace = await self._resolve_shift_for_date(
                org_id=org_id, employee_id=record.employee_id, work_date=record.work_date
            )
            expected_start = datetime.combine(record.work_date, start_time, tzinfo=timezone.utc) if start_time else None
            record.shift_id = shift_id
            record.shift_assignment_id = assignment_id
            derived = self._derive(
                status=record.status,
                clock_in_at=record.clock_in_at,
                clock_out_at=record.clock_out_at,
                expected_start=expected_start,
                grace_minutes=grace,
            )
            record.status = derived.status
            record.is_late = derived.is_late
            record.minutes_late = derived.minutes_late
            record.missing_checkout = derived.missing_checkout
            record.worked_minutes = derived.worked_minutes
            record.overtime_minutes = derived.overtime_minutes
            record.payable_hours = derived.payable_hours
            await self.attendance_repo.upsert_record(record)
        return corr

