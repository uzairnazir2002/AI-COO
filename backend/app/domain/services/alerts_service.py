from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from statistics import median, pstdev

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.alert import Alert
from app.domain.models.monthly_aggregate import MonthlyAggregate
from app.domain.models.organization_setting import OrganizationSetting
from app.domain.models.transaction import Transaction
from app.domain.repos.alerts_repo import AlertRepo


class AlertsService:
    def __init__(self, db: AsyncSession, repo: AlertRepo):
        self.db = db
        self.repo = repo

    async def list_alerts(self, org_id, status):
        return await self.repo.list_alerts(org_id, status)

    async def dismiss(self, alert):
        alert.status = "DISMISSED"
        await self.repo.save(alert)

    async def detect_and_create(self, org_id):
        settings = await self.db.scalar(select(OrganizationSetting).where(OrganizationSetting.org_id == org_id))
        anomaly_mult = Decimal(str(getattr(settings, "anomaly_spike_multiplier", Decimal("1.5"))))
        vendor_threshold = Decimal(
            str(getattr(settings, "vendor_concentration_threshold_pct", Decimal("50.00")))
        )
        misc_growth_mult = Decimal(str(getattr(settings, "misc_growth_multiplier", Decimal("1.4"))))
        created = 0
        created += await self._detect_anomaly(org_id, anomaly_mult)
        created += await self._detect_vendor_concentration(org_id, vendor_threshold)
        created += await self._detect_misc_growth(org_id, misc_growth_mult)
        created += await self._detect_margin_decline(org_id)
        created += await self._detect_subscription_creep(org_id)
        return created

    async def _create_if_new(self, alert: Alert) -> int:
        existing = await self.db.execute(
            select(Alert).where(
                Alert.org_id == alert.org_id,
                Alert.kind == alert.kind,
                Alert.title == alert.title,
                Alert.status == "OPEN",
            )
        )
        if existing.scalar_one_or_none():
            return 0
        await self.repo.save(alert)
        return 1

    async def _detect_anomaly(self, org_id, spike_multiplier: Decimal):
        created = 0
        since = date.today() - timedelta(days=180)
        month_expr = func.date_trunc("month", Transaction.date)
        q = await self.db.execute(
            select(Transaction.category, month_expr, func.sum(Transaction.amount))
            .where(Transaction.org_id == org_id, Transaction.type == "EXPENSE", Transaction.date >= since)
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
                created += await self._create_if_new(
                    Alert(
                        org_id=org_id,
                        kind="ANOMALY",
                        severity="HIGH",
                        title=f"Expense spike in {cat}",
                        description=f"Spend increased by {variance}% (method: {detection_method})",
                        meta={
                            "variance_pct": str(variance),
                            "impact": str((latest - baseline).quantize(Decimal("0.01"))),
                            "method": detection_method,
                            "score": str(score.quantize(Decimal("0.01"))),
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

    async def _detect_vendor_concentration(self, org_id, threshold_pct: Decimal):
        since = date.today() - timedelta(days=30)
        q = await self.db.execute(
            select(Transaction.vendor, func.sum(Transaction.amount))
            .where(Transaction.org_id == org_id, Transaction.type == "EXPENSE", Transaction.date >= since, Transaction.vendor.is_not(None))
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
            return await self._create_if_new(
                Alert(
                    org_id=org_id,
                    kind="PROFIT_LEAK",
                    severity="MEDIUM",
                    title="Vendor concentration risk",
                    description=f"Top vendor {top_vendor} accounts for {share.quantize(Decimal('0.01'))}% of spend.",
                    meta={"vendor": top_vendor, "share_pct": str(share.quantize(Decimal('0.01')))},
                ),
            )
        return 0

    async def _detect_misc_growth(self, org_id, growth_multiplier: Decimal):
        month_expr = func.date_trunc("month", Transaction.date)
        q = await self.db.execute(
            select(month_expr, func.sum(Transaction.amount))
            .where(Transaction.org_id == org_id, Transaction.type == "EXPENSE", Transaction.category.ilike("misc%"))
            .group_by(month_expr)
            .order_by(month_expr)
        )
        vals = [Decimal(x[1]) for x in q.all()]
        if len(vals) < 3:
            return 0
        baseline = sum(vals[:-1]) / Decimal(str(len(vals) - 1))
        latest = vals[-1]
        if baseline > 0 and latest > baseline * growth_multiplier:
            return await self._create_if_new(
                Alert(
                    org_id=org_id,
                    kind="PROFIT_LEAK",
                    severity="MEDIUM",
                    title="Misc category growth",
                    description="Misc expenses are growing faster than baseline.",
                    meta={"baseline": str(baseline), "latest": str(latest)},
                ),
            )
        return 0

    async def _detect_margin_decline(self, org_id):
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
        if latest.net_total < prev.net_total:
            return await self._create_if_new(
                Alert(
                    org_id=org_id,
                    kind="PROFIT_LEAK",
                    severity="HIGH",
                    title="Margin decline detected",
                    description="Net profit trend is declining month-over-month.",
                    meta={"previous_net": str(prev.net_total), "latest_net": str(latest.net_total)},
                ),
            )
        return 0

    async def _detect_subscription_creep(self, org_id):
        month_expr = func.date_trunc("month", Transaction.date)
        q = await self.db.execute(
            select(Transaction.vendor, month_expr, func.sum(Transaction.amount))
            .where(
                Transaction.org_id == org_id,
                Transaction.type == "EXPENSE",
                Transaction.vendor.is_not(None),
                Transaction.category.ilike("%subscription%"),
            )
            .group_by(Transaction.vendor, month_expr)
            .order_by(Transaction.vendor, month_expr)
        )
        by_vendor = defaultdict(list)
        for vendor, month, amount in q.all():
            by_vendor[vendor].append(Decimal(amount))

        for vendor, vals in by_vendor.items():
            if len(vals) >= 3 and vals[-1] > vals[-2] > vals[-3]:
                return await self._create_if_new(
                    Alert(
                        org_id=org_id,
                        kind="PROFIT_LEAK",
                        severity="MEDIUM",
                        title="Subscription creep",
                        description=f"Recurring spend with {vendor} is increasing for 3+ months.",
                        meta={"vendor": vendor, "series": [str(v) for v in vals[-3:]]},
                    ),
                )
        return 0
