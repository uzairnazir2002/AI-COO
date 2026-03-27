import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.models.budget import Budget
from app.domain.repos.budget_repo import BudgetRepo


@dataclass(slots=True)
class BudgetVarianceLine:
    category: str
    budget_type: str
    planned_amount: Decimal
    actual_amount: Decimal
    variance_amount: Decimal
    variance_pct: Decimal | None


class BudgetService:
    def __init__(self, repo: BudgetRepo):
        self.repo = repo

    @staticmethod
    def _normalize_period_month(period_month: date) -> date:
        return period_month.replace(day=1)

    @staticmethod
    def _month_end_exclusive(period_month: date) -> date:
        month_start = period_month.replace(day=1)
        if month_start.month == 12:
            return date(month_start.year + 1, 1, 1)
        return date(month_start.year, month_start.month + 1, 1)

    @staticmethod
    def _normalize_budget_type(value: str | None) -> str:
        normalized = str(value or "EXPENSE").strip().upper()
        if normalized not in {"EXPENSE", "REVENUE"}:
            raise ValueError("budget_type must be EXPENSE or REVENUE")
        return normalized

    @staticmethod
    def _normalize_category(value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("category is required")
        return normalized

    async def list_budgets(
        self,
        *,
        org_id: uuid.UUID,
        period_month: date | None = None,
        budget_type: str | None = None,
        include_history: bool = False,
    ) -> list[Budget]:
        normalized_period = self._normalize_period_month(period_month) if period_month else None
        normalized_type = self._normalize_budget_type(budget_type) if budget_type else None
        return await self.repo.list_budgets(
            org_id=org_id,
            period_month=normalized_period,
            budget_type=normalized_type,
            include_history=include_history,
        )

    async def create_budget(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        category: str,
        period_month: date,
        planned_amount: Decimal,
        budget_type: str = "EXPENSE",
        notes: str | None = None,
    ) -> Budget:
        normalized_category = self._normalize_category(category)
        normalized_period = self._normalize_period_month(period_month)
        normalized_type = self._normalize_budget_type(budget_type)
        version = (
            await self.repo.max_version(
                org_id=org_id,
                category=normalized_category,
                period_month=normalized_period,
                budget_type=normalized_type,
            )
            + 1
        )
        await self.repo.clear_current(
            org_id=org_id,
            category=normalized_category,
            period_month=normalized_period,
            budget_type=normalized_type,
        )
        return await self.repo.save(
            Budget(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                category=normalized_category,
                period_month=normalized_period,
                budget_type=normalized_type,
                planned_amount=planned_amount,
                notes=notes,
                version=version,
                is_current=True,
            )
        )

    async def update_budget_version(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        budget_id: uuid.UUID,
        planned_amount: Decimal,
        notes: str | None = None,
    ) -> Budget:
        current = await self.repo.get_budget(budget_id=budget_id, org_id=org_id)
        if not current:
            raise ValueError("Budget not found")
        return await self.create_budget(
            org_id=org_id,
            actor_user_id=actor_user_id,
            category=current.category,
            period_month=current.period_month,
            planned_amount=planned_amount,
            budget_type=current.budget_type,
            notes=notes if notes is not None else current.notes,
        )

    async def budget_variance(
        self,
        *,
        org_id: uuid.UUID,
        period_month: date,
        budget_type: str | None = None,
        location_id: uuid.UUID | None = None,
    ) -> dict:
        normalized_period = self._normalize_period_month(period_month)
        normalized_type = self._normalize_budget_type(budget_type) if budget_type else None
        budgets = await self.repo.list_budgets(
            org_id=org_id,
            period_month=normalized_period,
            budget_type=normalized_type,
            include_history=False,
        )
        period_end = self._month_end_exclusive(normalized_period)
        if normalized_type:
                actuals_by_type: dict[str, dict[str, Decimal]] = {
                    normalized_type: await self.repo.monthly_actuals_by_category(
                        org_id=org_id,
                        period_start=normalized_period,
                        period_end_exclusive=period_end,
                        budget_type=normalized_type,
                        location_id=location_id,
                    )
                }
        else:
            actuals_by_type = {
                "EXPENSE": await self.repo.monthly_actuals_by_category(
                    org_id=org_id,
                    period_start=normalized_period,
                    period_end_exclusive=period_end,
                    budget_type="EXPENSE",
                    location_id=location_id,
                ),
                "REVENUE": await self.repo.monthly_actuals_by_category(
                    org_id=org_id,
                    period_start=normalized_period,
                    period_end_exclusive=period_end,
                    budget_type="REVENUE",
                    location_id=location_id,
                ),
            }
        lines: list[BudgetVarianceLine] = []
        budgeted_pairs: set[tuple[str, str]] = set()
        planned_total = Decimal("0")
        actual_total = Decimal("0")

        for budget in budgets:
            category = str(budget.category)
            budget_type_key = str(budget.budget_type).upper()
            budgeted_pairs.add((budget_type_key, category))
            planned = Decimal(budget.planned_amount or 0).quantize(Decimal("0.01"))
            actual = Decimal(actuals_by_type.get(budget_type_key, {}).get(category, Decimal("0"))).quantize(
                Decimal("0.01")
            )
            variance = (actual - planned).quantize(Decimal("0.01"))
            variance_pct = None
            if planned != 0:
                variance_pct = ((variance / planned) * Decimal("100")).quantize(Decimal("0.01"))
            lines.append(
                BudgetVarianceLine(
                    category=category,
                    budget_type=budget_type_key,
                    planned_amount=planned,
                    actual_amount=actual,
                    variance_amount=variance,
                    variance_pct=variance_pct,
                )
            )
            planned_total += planned
            actual_total += actual

        for actual_type, actual_map in actuals_by_type.items():
            for category, actual in actual_map.items():
                if (actual_type, category) in budgeted_pairs:
                    continue
                actual_q = Decimal(actual).quantize(Decimal("0.01"))
                lines.append(
                    BudgetVarianceLine(
                        category=category,
                        budget_type=actual_type,
                        planned_amount=Decimal("0.00"),
                        actual_amount=actual_q,
                        variance_amount=actual_q,
                        variance_pct=None,
                    )
                )
                actual_total += actual_q

        variance_total = (actual_total - planned_total).quantize(Decimal("0.01"))
        lines.sort(key=lambda row: abs(row.variance_amount), reverse=True)
        return {
            "org_id": org_id,
            "period_month": normalized_period,
            "budget_type": normalized_type or "ALL",
            "totals": {
                "planned_amount": planned_total.quantize(Decimal("0.01")),
                "actual_amount": actual_total.quantize(Decimal("0.01")),
                "variance_amount": variance_total,
            },
            "lines": lines,
        }
