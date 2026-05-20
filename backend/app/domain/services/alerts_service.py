from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from statistics import median, pstdev
import uuid

from sqlalchemy import Integer, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.alert import Alert
from app.domain.models.location import Location
from app.domain.models.monthly_aggregate import MonthlyAggregate
from app.domain.models.organization_setting import OrganizationSetting
from app.domain.models.transaction import Transaction
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.budget_repo import BudgetRepo
from app.domain.repos.inventory_repo import InventoryRepo
from app.domain.repos.location_repo import LocationRepo
from app.domain.models.workforce_attendance_record import WorkforceAttendanceRecord
from app.domain.models.workforce_employee import WorkforceEmployee
from app.domain.models.workforce_leave_request import WorkforceLeaveRequest
from app.domain.models.workforce_payroll_entry import WorkforcePayrollEntry
from app.domain.models.workforce_payroll_period import WorkforcePayrollPeriod
from app.domain.models.workforce_announcement import WorkforceAnnouncement
from app.domain.models.workforce_announcement_receipt import WorkforceAnnouncementReceipt
from app.domain.services.budget_service import BudgetService
from app.domain.services.inventory_service import InventoryService


class AlertsService:
    def __init__(self, db: AsyncSession, repo: AlertRepo, audit_repo: AuditRepo | None = None):
        self.db = db
        self.repo = repo
        self.audit_repo = audit_repo

    async def list_alerts(self, org_id, status, assigned_to_user_id=None, location_id=None):
        rows = await self.repo.list_alerts(
            org_id,
            status,
            assigned_to_user_id=assigned_to_user_id,
            location_id=location_id,
        )
        return sorted(rows, key=self._alert_rank_key, reverse=True)

    @staticmethod
    def _alert_rank_key(alert: Alert):
        severity_weight = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(str(alert.severity).upper(), 0)
        meta = alert.meta or {}
        impact_raw = meta.get("impact") or meta.get("variance_pct") or meta.get("share_pct") or "0"
        try:
            impact_val = abs(Decimal(str(impact_raw)))
        except Exception:
            impact_val = Decimal("0")
        return (severity_weight, impact_val, alert.created_at.timestamp())

    async def dismiss(self, alert):
        alert.status = "DISMISSED"
        await self.repo.save(alert)

    @staticmethod
    def _utc_now_naive() -> datetime:
        # alerts.assigned_at / acknowledged_at are stored as TIMESTAMP WITHOUT TIME ZONE.
        return datetime.now(timezone.utc).replace(tzinfo=None)

    async def assign(self, *, alert: Alert, assignee_user_id: uuid.UUID | None, actor_user_id: uuid.UUID):
        alert.assigned_to_user_id = assignee_user_id
        alert.assigned_by_user_id = actor_user_id
        alert.assigned_at = self._utc_now_naive()
        alert.acknowledged_at = None
        await self.repo.save(alert)

    async def acknowledge(self, *, alert: Alert):
        alert.acknowledged_at = self._utc_now_naive()
        await self.repo.save(alert)

    async def detect_and_create(self, org_id):
        settings = await self.db.scalar(select(OrganizationSetting).where(OrganizationSetting.org_id == org_id))
        anomaly_mult = Decimal(str(getattr(settings, "anomaly_spike_multiplier", Decimal("1.5"))))
        vendor_threshold = Decimal(
            str(getattr(settings, "vendor_concentration_threshold_pct", Decimal("50.00")))
        )
        budget_threshold = Decimal(
            str(getattr(settings, "budget_variance_alert_threshold_pct", Decimal("10.00")))
        )
        misc_growth_mult = Decimal(str(getattr(settings, "misc_growth_multiplier", Decimal("1.4"))))
        contexts = await self._detection_contexts(org_id)
        created = 0
        for location in contexts:
            created += await self._detect_anomaly(org_id, anomaly_mult, location=location)
            created += await self._detect_vendor_concentration(org_id, vendor_threshold, location=location)
            created += await self._detect_budget_threshold(org_id, budget_threshold, location=location)
            created += await self._detect_misc_growth(org_id, misc_growth_mult, location=location)
            created += await self._detect_margin_decline(org_id, location=location)
            created += await self._detect_subscription_creep(org_id, location=location)
            created += await self._detect_inventory_stockout_risk(org_id, location=location)
            # Phase 7 — Workforce intelligence alerts (org-wide only; location ignored for now).
            if location is None:
                created += await self._detect_workforce_missing_checkout(org_id)
                created += await self._detect_workforce_repeated_lateness(org_id)
                created += await self._detect_workforce_pending_leave(org_id)
                created += await self._detect_workforce_payroll_due(org_id)
                created += await self._detect_workforce_unpaid_payroll(org_id)
                created += await self._detect_workforce_high_absenteeism(org_id)
                created += await self._detect_workforce_overtime_threshold(org_id)
                created += await self._detect_workforce_contract_expiry(org_id)
                created += await self._detect_workforce_announcement_ack(org_id)
        return created

    async def _detect_workforce_missing_checkout(self, org_id: uuid.UUID) -> int:
        today = date.today()
        count = await self.db.scalar(
            select(func.count()).select_from(WorkforceAttendanceRecord).where(
                WorkforceAttendanceRecord.org_id == org_id,
                WorkforceAttendanceRecord.work_date == today,
                WorkforceAttendanceRecord.missing_checkout.is_(True),
            )
        )
        c = int(count or 0)
        if c <= 0:
            return 0
        return await self._create_if_new(
            Alert(
                org_id=org_id,
                location_id=None,
                kind="ANOMALY",
                severity="MEDIUM" if c < 3 else "HIGH",
                title=f"Missing check-outs detected ({c})",
                description=f"{c} attendance records are missing a check-out for {today.isoformat()}.",
                meta={"subkind": "WORKFORCE_MISSING_CHECKOUT", "date": today.isoformat(), "count": c, "impact": str(c)},
            ),
            audit_action="alert.detect.workforce_missing_checkout",
            audit_metadata={"date": today.isoformat(), "count": c},
        )

    async def _detect_workforce_repeated_lateness(self, org_id: uuid.UUID) -> int:
        # Flag if any employee has >= 3 late days in last 14 days.
        end = date.today()
        start = end - timedelta(days=13)
        rows = await self.db.execute(
            select(
                WorkforceAttendanceRecord.employee_id,
                func.sum(func.cast(WorkforceAttendanceRecord.is_late, Integer)).label("late_days"),
            )
            .where(
                WorkforceAttendanceRecord.org_id == org_id,
                WorkforceAttendanceRecord.work_date >= start,
                WorkforceAttendanceRecord.work_date <= end,
            )
            .group_by(WorkforceAttendanceRecord.employee_id)
            .having(func.sum(func.cast(WorkforceAttendanceRecord.is_late, Integer)) >= 3)
            .limit(5)
        )
        top = [(str(emp_id), int(late_days or 0)) for emp_id, late_days in rows.all()]
        if not top:
            return 0
        max_late = max(v for _, v in top)
        return await self._create_if_new(
            Alert(
                org_id=org_id,
                location_id=None,
                kind="ANOMALY",
                severity="MEDIUM" if max_late < 5 else "HIGH",
                title="Repeated lateness risk",
                description=f"At least {len(top)} employees have 3+ late days in the last 14 days.",
                meta={
                    "subkind": "WORKFORCE_REPEATED_LATENESS",
                    "from": start.isoformat(),
                    "to": end.isoformat(),
                    "top": top,
                    "impact": str(max_late),
                },
            ),
            audit_action="alert.detect.workforce_repeated_lateness",
            audit_metadata={"from": start.isoformat(), "to": end.isoformat(), "top": top},
        )

    async def _detect_workforce_pending_leave(self, org_id: uuid.UUID) -> int:
        count = await self.db.scalar(
            select(func.count()).select_from(WorkforceLeaveRequest).where(
                WorkforceLeaveRequest.org_id == org_id,
                WorkforceLeaveRequest.status == "PENDING",
            )
        )
        c = int(count or 0)
        if c <= 0:
            return 0
        return await self._create_if_new(
            Alert(
                org_id=org_id,
                location_id=None,
                kind="ANOMALY",
                severity="LOW" if c < 5 else "MEDIUM",
                title=f"Pending leave approvals ({c})",
                description="There are pending leave requests awaiting review.",
                meta={"subkind": "WORKFORCE_PENDING_LEAVE", "count": c, "impact": str(c)},
            ),
            audit_action="alert.detect.workforce_pending_leave",
            audit_metadata={"count": c},
        )

    async def _detect_workforce_payroll_due(self, org_id: uuid.UUID) -> int:
        today = date.today()
        due_end = today + timedelta(days=7)
        periods = await self.db.scalar(
            select(func.count()).select_from(WorkforcePayrollPeriod).where(
                WorkforcePayrollPeriod.org_id == org_id,
                WorkforcePayrollPeriod.status != "PAID",
                WorkforcePayrollPeriod.end_date <= due_end,
            )
        )
        unpaid = await self.db.scalar(
            select(func.count()).select_from(WorkforcePayrollEntry).where(
                WorkforcePayrollEntry.org_id == org_id,
                WorkforcePayrollEntry.status != "PAID",
            )
        )
        p = int(periods or 0)
        u = int(unpaid or 0)
        if p <= 0 and u <= 0:
            return 0
        sev = "MEDIUM" if p > 0 else "LOW"
        return await self._create_if_new(
            Alert(
                org_id=org_id,
                location_id=None,
                kind="RUNWAY",
                severity=sev,
                title="Payroll due soon",
                description=f"{p} payroll periods end within 7 days; {u} entries are not marked paid.",
                meta={"subkind": "WORKFORCE_PAYROLL_DUE", "due_periods": p, "unpaid_entries": u, "impact": str(max(p, u))},
            ),
            audit_action="alert.detect.workforce_payroll_due",
            audit_metadata={"due_periods": p, "unpaid_entries": u},
        )

    async def _detect_workforce_unpaid_payroll(self, org_id: uuid.UUID) -> int:
        unpaid = await self.db.scalar(
            select(func.count()).select_from(WorkforcePayrollEntry).where(
                WorkforcePayrollEntry.org_id == org_id,
                WorkforcePayrollEntry.status != "PAID",
            )
        )
        u = int(unpaid or 0)
        if u <= 0:
            return 0
        return await self._create_if_new(
            Alert(
                org_id=org_id,
                location_id=None,
                kind="RUNWAY",
                severity="MEDIUM" if u < 25 else "HIGH",
                title=f"Unpaid payroll entries ({u})",
                description="Payroll entries remain unpaid and need settlement.",
                meta={"subkind": "WORKFORCE_UNPAID_PAYROLL", "count": u, "impact": str(u)},
            ),
            audit_action="alert.detect.workforce_unpaid_payroll",
            audit_metadata={"count": u},
        )

    async def _detect_workforce_high_absenteeism(self, org_id: uuid.UUID) -> int:
        end = date.today()
        start = end - timedelta(days=13)
        rows = await self.db.execute(
            select(
                func.count().label("total"),
                func.sum(case((WorkforceAttendanceRecord.status == "ABSENT", 1), else_=0)).label("absent"),
            ).where(
                WorkforceAttendanceRecord.org_id == org_id,
                WorkforceAttendanceRecord.work_date >= start,
                WorkforceAttendanceRecord.work_date <= end,
            )
        )
        total, absent = rows.one()
        t = int(total or 0)
        a = int(absent or 0)
        if t <= 0:
            return 0
        ratio = (Decimal(a) / Decimal(t) * Decimal("100")).quantize(Decimal("0.01"))
        if ratio < Decimal("15.00"):
            return 0
        sev = "MEDIUM" if ratio < Decimal("25.00") else "HIGH"
        return await self._create_if_new(
            Alert(
                org_id=org_id,
                location_id=None,
                kind="ANOMALY",
                severity=sev,
                title=f"High absenteeism risk ({ratio}%)",
                description=f"Absence rate is elevated over the last 14 days ({a}/{t} records).",
                meta={
                    "subkind": "WORKFORCE_HIGH_ABSENTEEISM",
                    "from": start.isoformat(),
                    "to": end.isoformat(),
                    "absent": a,
                    "total": t,
                    "absence_rate_pct": str(ratio),
                    "impact": str(ratio),
                },
            ),
            audit_action="alert.detect.workforce_high_absenteeism",
            audit_metadata={"from": start.isoformat(), "to": end.isoformat(), "absence_rate_pct": str(ratio)},
        )

    async def _detect_workforce_overtime_threshold(self, org_id: uuid.UUID) -> int:
        end = date.today()
        start = end - timedelta(days=29)
        rows = await self.db.execute(
            select(
                WorkforceAttendanceRecord.employee_id,
                func.sum(func.coalesce(WorkforceAttendanceRecord.overtime_minutes, 0)).label("ot_minutes"),
            )
            .where(
                WorkforceAttendanceRecord.org_id == org_id,
                WorkforceAttendanceRecord.work_date >= start,
                WorkforceAttendanceRecord.work_date <= end,
            )
            .group_by(WorkforceAttendanceRecord.employee_id)
            .having(func.sum(func.coalesce(WorkforceAttendanceRecord.overtime_minutes, 0)) >= 600)
            .limit(10)
        )
        top = [(str(emp_id), int(ot_minutes or 0)) for emp_id, ot_minutes in rows.all()]
        if not top:
            return 0
        max_ot = max(v for _, v in top)
        return await self._create_if_new(
            Alert(
                org_id=org_id,
                location_id=None,
                kind="ANOMALY",
                severity="MEDIUM" if max_ot < 1200 else "HIGH",
                title="Overtime threshold breach",
                description=f"{len(top)} employees crossed overtime threshold in the last 30 days.",
                meta={
                    "subkind": "WORKFORCE_OVERTIME_THRESHOLD",
                    "from": start.isoformat(),
                    "to": end.isoformat(),
                    "threshold_minutes": 600,
                    "top": top,
                    "impact": str(max_ot),
                },
            ),
            audit_action="alert.detect.workforce_overtime_threshold",
            audit_metadata={"from": start.isoformat(), "to": end.isoformat(), "top": top},
        )

    async def _detect_workforce_contract_expiry(self, org_id: uuid.UUID) -> int:
        today = date.today()
        window_end = today + timedelta(days=30)
        expiring = await self.db.scalar(
            select(func.count()).select_from(WorkforceEmployee).where(
                WorkforceEmployee.org_id == org_id,
                WorkforceEmployee.is_active.is_(True),
                WorkforceEmployee.contract_end.is_not(None),
                WorkforceEmployee.contract_end >= today,
                WorkforceEmployee.contract_end <= window_end,
            )
        )
        c = int(expiring or 0)
        if c <= 0:
            return 0
        return await self._create_if_new(
            Alert(
                org_id=org_id,
                location_id=None,
                kind="ANOMALY",
                severity="LOW" if c < 3 else "MEDIUM",
                title=f"Contracts expiring soon ({c})",
                description="Some employee contracts are expiring within 30 days.",
                meta={"subkind": "WORKFORCE_CONTRACT_EXPIRY", "count": c, "window_days": 30, "impact": str(c)},
            ),
            audit_action="alert.detect.workforce_contract_expiry",
            audit_metadata={"count": c, "window_days": 30},
        )

    async def _detect_workforce_announcement_ack(self, org_id: uuid.UUID) -> int:
        today = date.today()
        ann_rows = await self.db.execute(
            select(WorkforceAnnouncement.id)
            .where(
                WorkforceAnnouncement.org_id == org_id,
                WorkforceAnnouncement.status == "PUBLISHED",
                WorkforceAnnouncement.acknowledgement_required.is_(True),
                WorkforceAnnouncement.published_at.is_not(None),
                func.coalesce(WorkforceAnnouncement.expires_at, today) >= today,
            )
            .limit(200)
        )
        announcement_ids = [r[0] for r in ann_rows.all()]
        if not announcement_ids:
            return 0
        acked = await self.db.execute(
            select(WorkforceAnnouncementReceipt.announcement_id)
            .where(
                WorkforceAnnouncementReceipt.announcement_id.in_(announcement_ids),
                WorkforceAnnouncementReceipt.acknowledged_at.is_not(None),
            )
            .group_by(WorkforceAnnouncementReceipt.announcement_id)
        )
        acked_set = {r[0] for r in acked.all()}
        unacked = sum(1 for a_id in announcement_ids if a_id not in acked_set)
        if unacked <= 0:
            return 0
        return await self._create_if_new(
            Alert(
                org_id=org_id,
                location_id=None,
                kind="ANOMALY",
                severity="LOW" if unacked < 3 else "MEDIUM",
                title=f"Announcements need acknowledgement ({unacked})",
                description="Some critical announcements still need acknowledgement.",
                meta={"subkind": "WORKFORCE_ANNOUNCEMENT_ACK", "count": unacked, "impact": str(unacked)},
            ),
            audit_action="alert.detect.workforce_announcement_ack",
            audit_metadata={"count": unacked},
        )

    async def _detection_contexts(self, org_id: uuid.UUID) -> list[Location | None]:
        active_locations = await LocationRepo(self.db).list_by_org(org_id=org_id, include_inactive=False)
        return [None, *active_locations]

    async def _create_if_new(
        self,
        alert: Alert,
        *,
        audit_action: str | None = None,
        audit_metadata: dict | None = None,
    ) -> int:
        location_filter = (
            Alert.location_id == alert.location_id
            if alert.location_id is not None
            else Alert.location_id.is_(None)
        )
        existing = await self.db.execute(
            select(Alert).where(
                Alert.org_id == alert.org_id,
                location_filter,
                Alert.kind == alert.kind,
                Alert.title == alert.title,
                Alert.status == "OPEN",
            )
        )
        if existing.scalar_one_or_none():
            return 0
        await self.repo.save(alert)
        if self.audit_repo and audit_action:
            await self.audit_repo.log(
                actor_user_id=None,
                org_id=alert.org_id,
                action=audit_action,
                entity_type="alert",
                entity_id=str(alert.id),
                metadata_json=audit_metadata or (alert.meta or {}),
            )
        return 1

    @staticmethod
    def _location_filters(location: Location | None) -> list:
        if location is None:
            return []
        return [Transaction.location_id == location.id]

    @staticmethod
    def _location_suffix(location: Location | None) -> str:
        if location is None:
            return ""
        return f" at {location.name}"

    @staticmethod
    def _location_meta(location: Location | None) -> dict[str, str]:
        if location is None:
            return {}
        return {"location_id": str(location.id), "location_name": location.name}

    async def _detect_budget_threshold(self, org_id, threshold_pct: Decimal, *, location: Location | None):
        if threshold_pct <= 0:
            return 0
        period_month = date.today().replace(day=1)
        variance = await BudgetService(BudgetRepo(self.db)).budget_variance(
            org_id=org_id,
            period_month=period_month,
            budget_type="EXPENSE",
            location_id=location.id if location else None,
        )
        created = 0
        period_label = period_month.strftime("%Y-%m")
        suffix = self._location_suffix(location)
        for line in variance.get("lines", []):
            planned = Decimal(str(getattr(line, "planned_amount", "0")))
            variance_pct_raw = getattr(line, "variance_pct", None)
            if planned <= 0 or variance_pct_raw is None:
                continue
            variance_pct = Decimal(str(variance_pct_raw))
            variance_amount = Decimal(str(getattr(line, "variance_amount", "0")))
            if variance_pct < threshold_pct or variance_amount <= 0:
                continue

            actual = Decimal(str(getattr(line, "actual_amount", "0")))
            category = str(getattr(line, "category", "Uncategorized"))
            variance_pct_q = variance_pct.quantize(Decimal("0.01"))
            variance_amount_q = variance_amount.quantize(Decimal("0.01"))
            severity = "HIGH" if variance_pct >= threshold_pct * Decimal("2") else "MEDIUM"
            created += await self._create_if_new(
                Alert(
                    org_id=org_id,
                    location_id=location.id if location else None,
                    kind="PROFIT_LEAK",
                    severity=severity,
                    title=f"Budget threshold exceeded in {category}{suffix} ({period_label})",
                    description=f"{category} is {variance_pct_q}% over budget for {period_label}{suffix}.",
                    meta={
                        "subkind": "BUDGET_THRESHOLD",
                        "category": category,
                        "period_month": period_label,
                        "planned_amount": str(planned.quantize(Decimal("0.01"))),
                        "actual_amount": str(actual.quantize(Decimal("0.01"))),
                        "variance_amount": str(variance_amount_q),
                        "variance_pct": str(variance_pct_q),
                        "threshold_pct": str(threshold_pct.quantize(Decimal("0.01"))),
                        "impact": str(variance_amount_q),
                        **self._location_meta(location),
                    },
                ),
                audit_action="alert.detect.budget_threshold",
                audit_metadata={
                    "category": category,
                    "period_month": period_label,
                    "variance_pct": str(variance_pct_q),
                    "threshold_pct": str(threshold_pct.quantize(Decimal("0.01"))),
                    "severity": severity,
                    **self._location_meta(location),
                },
            )
        return created

    async def _detect_inventory_stockout_risk(self, org_id, *, location: Location | None):
        forecast = await InventoryService(InventoryRepo(self.db)).forecast(
            org_id=org_id,
            lookback_days=30,
            horizon_days=30,
            location_id=location.id if location else None,
        )
        rows = forecast.get("items", [])
        if not rows:
            return 0
        suffix = self._location_suffix(location)
        created = 0
        for row in rows:
            if isinstance(row, dict):
                item_id_raw = row.get("item_id")
                sku = str(row.get("sku") or "UNKNOWN")
                item_name = str(row.get("name") or sku)
                location_id_raw = row.get("location_id")
                risk_level = str(row.get("risk_level") or "").upper()
                days_of_cover_raw = row.get("days_of_cover")
                projected_stockout_date_raw = row.get("projected_stockout_date")
                on_hand_qty_raw = row.get("on_hand_qty")
                reorder_point_raw = row.get("reorder_point")
                units_per_day_raw = row.get("units_per_day")
                cogs_exposure_raw = row.get("cogs_exposure_30d")
            else:
                item_id_raw = getattr(row, "item_id", None)
                sku = str(getattr(row, "sku", "UNKNOWN"))
                item_name = str(getattr(row, "name", sku))
                location_id_raw = getattr(row, "location_id", None)
                risk_level = str(getattr(row, "risk_level", "")).upper()
                days_of_cover_raw = getattr(row, "days_of_cover", None)
                projected_stockout_date_raw = getattr(row, "projected_stockout_date", None)
                on_hand_qty_raw = getattr(row, "on_hand_qty", None)
                reorder_point_raw = getattr(row, "reorder_point", None)
                units_per_day_raw = getattr(row, "units_per_day", None)
                cogs_exposure_raw = getattr(row, "cogs_exposure_30d", None)

            if risk_level != "HIGH":
                continue
            if item_id_raw is None:
                continue
            item_id = uuid.UUID(str(item_id_raw))
            row_location_id = uuid.UUID(str(location_id_raw)) if location_id_raw else None
            if location is None and row_location_id is not None:
                continue
            if location is not None and row_location_id != location.id:
                continue

            try:
                on_hand_qty = Decimal(str(on_hand_qty_raw or "0")).quantize(Decimal("0.001"))
                reorder_point = Decimal(str(reorder_point_raw or "0")).quantize(Decimal("0.001"))
                units_per_day = Decimal(str(units_per_day_raw or "0")).quantize(Decimal("0.0001"))
                cogs_exposure = Decimal(str(cogs_exposure_raw or "0")).quantize(Decimal("0.01"))
                days_of_cover = (
                    Decimal(str(days_of_cover_raw)).quantize(Decimal("0.1"))
                    if days_of_cover_raw is not None
                    else None
                )
            except Exception:
                continue

            projected_stockout_date = str(projected_stockout_date_raw) if projected_stockout_date_raw else None
            cover_text = (
                f"{days_of_cover} days"
                if days_of_cover is not None
                else "no stable velocity baseline"
            )
            created += await self._create_if_new(
                Alert(
                    org_id=org_id,
                    location_id=row_location_id,
                    kind="ANOMALY",
                    severity="HIGH",
                    title=f"Inventory stockout risk: {sku}{suffix}",
                    description=f"{item_name} has high stockout risk ({cover_text}){suffix}.",
                    meta={
                        "subkind": "INVENTORY_STOCKOUT",
                        "item_id": str(item_id),
                        "sku": sku,
                        "name": item_name,
                        "on_hand_qty": str(on_hand_qty),
                        "reorder_point": str(reorder_point),
                        "units_per_day": str(units_per_day),
                        "days_of_cover": str(days_of_cover) if days_of_cover is not None else None,
                        "projected_stockout_date": projected_stockout_date,
                        "cogs_exposure_30d": str(cogs_exposure),
                        "impact": str(cogs_exposure),
                        **self._location_meta(location if location else None),
                    },
                ),
                audit_action="alert.detect.inventory_stockout",
                audit_metadata={
                    "item_id": str(item_id),
                    "sku": sku,
                    "days_of_cover": str(days_of_cover) if days_of_cover is not None else None,
                    "projected_stockout_date": projected_stockout_date,
                    **self._location_meta(location if location else None),
                },
            )
        return created

    async def _detect_anomaly(self, org_id, spike_multiplier: Decimal, *, location: Location | None):
        created = 0
        since = date.today() - timedelta(days=180)
        month_expr = func.date_trunc("month", Transaction.date)
        filters = [
            Transaction.org_id == org_id,
            Transaction.type == "EXPENSE",
            Transaction.date >= since,
            *self._location_filters(location),
        ]
        q = await self.db.execute(
            select(Transaction.category, month_expr, func.sum(Transaction.amount))
            .where(and_(*filters))
            .group_by(Transaction.category, month_expr)
            .order_by(Transaction.category, month_expr)
        )
        data = defaultdict(list)
        for cat, m, total in q.all():
            data[cat].append((m, Decimal(total)))

        for cat, points in data.items():
            vals = [v for _, v in sorted(points, key=lambda x: x[0])]
            if len(vals) < 3:
                continue
            latest = vals[-1]
            hist = vals[:-1]
            robust = self._robust_mad_score(hist, latest)
            z = self._z_score(hist, latest)
            is_spike = False
            detection_method = "none"
            score = Decimal("0")

            if robust is not None and robust >= Decimal("3.50"):
                is_spike = True
                detection_method = "MAD"
                score = robust
            elif z is not None and z >= Decimal("3.00"):
                is_spike = True
                detection_method = "Z_SCORE"
                score = z

            baseline = sum(hist) / Decimal(str(len(hist)))
            if baseline > 0 and latest > baseline * spike_multiplier:
                is_spike = True
                if detection_method == "none":
                    detection_method = "MULTIPLIER"
                    score = spike_multiplier

            if is_spike and baseline > 0:
                variance = ((latest - baseline) / baseline * Decimal("100")).quantize(Decimal("0.01"))
                suffix = self._location_suffix(location)
                created += await self._create_if_new(
                    Alert(
                        org_id=org_id,
                        location_id=location.id if location else None,
                        kind="ANOMALY",
                        severity="HIGH",
                        title=f"Expense spike in {cat}{suffix}",
                        description=f"Spend increased by {variance}%{suffix} (method: {detection_method})",
                        meta={
                            "variance_pct": str(variance),
                            "impact": str((latest - baseline).quantize(Decimal("0.01"))),
                            "method": detection_method,
                            "score": str(score.quantize(Decimal("0.01"))),
                            **self._location_meta(location),
                        },
                    ),
                )
        return created

    @staticmethod
    def _robust_mad_score(history: list[Decimal], latest: Decimal) -> Decimal | None:
        if len(history) < 2:
            return None
        hist_f = [float(v) for v in history]
        med = median(hist_f)
        abs_dev = [abs(x - med) for x in hist_f]
        mad = median(abs_dev)
        if mad == 0:
            return None
        score = 0.6745 * (float(latest) - med) / mad
        if score < 0:
            return Decimal("0")
        return Decimal(str(score))

    @staticmethod
    def _z_score(history: list[Decimal], latest: Decimal) -> Decimal | None:
        if len(history) < 2:
            return None
        hist_f = [float(v) for v in history]
        std = pstdev(hist_f)
        if std == 0:
            return None
        mu = sum(hist_f) / len(hist_f)
        score = (float(latest) - mu) / std
        if score < 0:
            return Decimal("0")
        return Decimal(str(score))

    async def _detect_vendor_concentration(self, org_id, threshold_pct: Decimal, *, location: Location | None):
        since = date.today() - timedelta(days=30)
        filters = [
            Transaction.org_id == org_id,
            Transaction.type == "EXPENSE",
            Transaction.date >= since,
            Transaction.vendor.is_not(None),
            *self._location_filters(location),
        ]
        q = await self.db.execute(
            select(Transaction.vendor, func.sum(Transaction.amount))
            .where(and_(*filters))
            .group_by(Transaction.vendor)
            .order_by(func.sum(Transaction.amount).desc())
        )
        rows = q.all()
        if not rows:
            return 0
        total = sum(Decimal(r[1]) for r in rows)
        top_vendor, top_amt = rows[0]
        share = (Decimal(top_amt) / total * Decimal("100")) if total > 0 else Decimal("0")
        if share >= threshold_pct:
            suffix = self._location_suffix(location)
            return await self._create_if_new(
                Alert(
                    org_id=org_id,
                    location_id=location.id if location else None,
                    kind="PROFIT_LEAK",
                    severity="MEDIUM",
                    title=f"Vendor concentration risk{suffix}",
                    description=f"Top vendor {top_vendor} accounts for {share.quantize(Decimal('0.01'))}% of spend{suffix}.",
                    meta={
                        "vendor": top_vendor,
                        "share_pct": str(share.quantize(Decimal("0.01"))),
                        **self._location_meta(location),
                    },
                ),
            )
        return 0

    async def _detect_misc_growth(self, org_id, growth_multiplier: Decimal, *, location: Location | None):
        month_expr = func.date_trunc("month", Transaction.date)
        filters = [
            Transaction.org_id == org_id,
            Transaction.type == "EXPENSE",
            Transaction.category.ilike("misc%"),
            *self._location_filters(location),
        ]
        q = await self.db.execute(
            select(month_expr, func.sum(Transaction.amount))
            .where(and_(*filters))
            .group_by(month_expr)
            .order_by(month_expr)
        )
        vals = [Decimal(x[1]) for x in q.all()]
        if len(vals) < 3:
            return 0
        baseline = sum(vals[:-1]) / Decimal(str(len(vals) - 1))
        latest = vals[-1]
        if baseline > 0 and latest > baseline * growth_multiplier:
            suffix = self._location_suffix(location)
            return await self._create_if_new(
                Alert(
                    org_id=org_id,
                    location_id=location.id if location else None,
                    kind="PROFIT_LEAK",
                    severity="MEDIUM",
                    title=f"Misc category growth{suffix}",
                    description=f"Misc expenses are growing faster than baseline{suffix}.",
                    meta={
                        "baseline": str(baseline),
                        "latest": str(latest),
                        **self._location_meta(location),
                    },
                ),
            )
        return 0

    async def _detect_margin_decline(self, org_id, *, location: Location | None):
        if location is None:
            q = await self.db.execute(
                select(MonthlyAggregate)
                .where(MonthlyAggregate.org_id == org_id)
                .order_by(MonthlyAggregate.year_month.desc())
                .limit(2)
            )
            rows = list(q.scalars().all())
            if len(rows) < 2:
                return 0
            latest, prev = rows[0], rows[1]
            latest_net = Decimal(str(latest.net_total))
            prev_net = Decimal(str(prev.net_total))
        else:
            month_expr = func.date_trunc("month", Transaction.date).label("month_start")
            q = await self.db.execute(
                select(
                    month_expr,
                    func.coalesce(
                        func.sum(
                            case(
                                (Transaction.type == "REVENUE", Transaction.amount),
                                else_=-Transaction.amount,
                            )
                        ),
                        0,
                    ).label("net_total"),
                )
                .where(
                    and_(
                        Transaction.org_id == org_id,
                        Transaction.location_id == location.id,
                    )
                )
                .group_by(month_expr)
                .order_by(month_expr.desc())
                .limit(2)
            )
            rows = q.all()
            if len(rows) < 2:
                return 0
            latest_net = Decimal(str(rows[0].net_total or 0))
            prev_net = Decimal(str(rows[1].net_total or 0))

        if latest_net < prev_net:
            suffix = self._location_suffix(location)
            return await self._create_if_new(
                Alert(
                    org_id=org_id,
                    location_id=location.id if location else None,
                    kind="PROFIT_LEAK",
                    severity="HIGH",
                    title=f"Margin decline detected{suffix}",
                    description=f"Net profit trend is declining month-over-month{suffix}.",
                    meta={
                        "previous_net": str(prev_net),
                        "latest_net": str(latest_net),
                        **self._location_meta(location),
                    },
                ),
            )
        return 0

    async def _detect_subscription_creep(self, org_id, *, location: Location | None):
        month_expr = func.date_trunc("month", Transaction.date)
        filters = [
            Transaction.org_id == org_id,
            Transaction.type == "EXPENSE",
            Transaction.vendor.is_not(None),
            Transaction.category.ilike("%subscription%"),
            *self._location_filters(location),
        ]
        q = await self.db.execute(
            select(Transaction.vendor, month_expr, func.sum(Transaction.amount))
            .where(and_(*filters))
            .group_by(Transaction.vendor, month_expr)
            .order_by(Transaction.vendor, month_expr)
        )
        by_vendor = defaultdict(list)
        for vendor, month, amount in q.all():
            by_vendor[vendor].append(Decimal(amount))

        for vendor, vals in by_vendor.items():
            if len(vals) >= 3 and vals[-1] > vals[-2] > vals[-3]:
                suffix = self._location_suffix(location)
                return await self._create_if_new(
                    Alert(
                        org_id=org_id,
                        location_id=location.id if location else None,
                        kind="PROFIT_LEAK",
                        severity="MEDIUM",
                        title=f"Subscription creep{suffix}",
                        description=f"Recurring spend with {vendor} is increasing for 3+ months{suffix}.",
                        meta={
                            "vendor": vendor,
                            "series": [str(v) for v in vals[-3:]],
                            **self._location_meta(location),
                        },
                    ),
                )
        return 0


    async def recompute(self, org_id):
        await self.repo.clear_open(org_id)
        return await self.detect_and_create(org_id)

