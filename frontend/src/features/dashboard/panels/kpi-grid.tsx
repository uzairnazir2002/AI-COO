"use client";

import { KpiCard } from "@/components/kpi/kpi-card";
import { formatCompactMoney, formatMoney } from "@/lib/utils/format";

type SparkPoint = { label: string; value: number };

export function DashboardKpiGrid({
  periodLabel,
  cashBalance,
  netChange,
  runwayDays,
  runwayAlert,
  burnRateMonthly,
  revenueMtd,
  expenseMtd,
  netMarginPct,
  sparklineData,
  burnSpark,
  budgetPlanned,
  budgetActual,
  budgetVarianceAmount,
  budgetVariancePct,
  hasBudgetVariance,
  onSelectMetric,
}: {
  periodLabel: string;
  cashBalance?: string | number | null;
  netChange: number;
  runwayDays?: number | null;
  runwayAlert?: boolean;
  burnRateMonthly?: string | number | null;
  revenueMtd: number;
  expenseMtd: number;
  netMarginPct: number;
  sparklineData: SparkPoint[];
  burnSpark: SparkPoint[];
  budgetPlanned: number;
  budgetActual: number;
  budgetVarianceAmount: number;
  budgetVariancePct: number;
  hasBudgetVariance: boolean;
  onSelectMetric: (metric: string) => void;
}) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <KpiCard
          label="Cash balance"
          value={formatMoney(cashBalance)}
          delta={netChange >= 0 ? "improving" : "under pressure"}
          insight="Current period"
          hint={periodLabel}
          sparklineData={sparklineData}
          onClick={() => onSelectMetric("Cash balance")}
        />
        <KpiCard
          label="Runway"
          value={`${runwayDays ?? 0} days`}
          warning={Boolean(runwayAlert)}
          delta={runwayAlert ? "watchlist" : "healthy"}
          insight="Conservative model"
          hint={runwayAlert ? "Below alert threshold" : "Healthy runway buffer"}
          sparklineData={sparklineData}
          onClick={() => onSelectMetric("Runway")}
        />
        <KpiCard
          label="Burn rate"
          value={formatCompactMoney(burnRateMonthly)}
          delta="rolling"
          insight="Monthly estimate"
          hint="Rolling burn estimate"
          sparklineData={burnSpark}
          onClick={() => onSelectMetric("Burn rate")}
        />
        <KpiCard
          label="Revenue MTD"
          value={formatCompactMoney(revenueMtd)}
          delta={revenueMtd > 0 ? "active" : "no data"}
          insight="Month to date"
          hint="Recognized revenue"
          onClick={() => onSelectMetric("Revenue MTD")}
        />
        <KpiCard
          label="Expense MTD"
          value={formatCompactMoney(expenseMtd)}
          delta={expenseMtd > 0 ? "active" : "no data"}
          insight="Month to date"
          hint="Recognized expenses"
          onClick={() => onSelectMetric("Expense MTD")}
        />
        <KpiCard
          label="Net margin"
          value={`${netMarginPct.toFixed(1)}%`}
          warning={netMarginPct < 0}
          delta={netMarginPct >= 0 ? "positive" : "negative"}
          insight="Based on MTD revenue/expense"
          hint="Profitability trend"
          onClick={() => onSelectMetric("Net margin")}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <KpiCard
          label="Budget planned (month)"
          value={formatMoney(budgetPlanned)}
          insight="Budget baseline"
          hint={hasBudgetVariance ? "Current month expense budget total" : "No monthly budgets configured"}
        />
        <KpiCard
          label="Budget actual (month)"
          value={formatMoney(budgetActual)}
          insight="Posted actuals"
          hint={hasBudgetVariance ? "Matched against expense transactions" : "No budget variance baseline yet"}
        />
        <KpiCard
          label="Budget variance (month)"
          value={formatMoney(budgetVarianceAmount)}
          warning={budgetVarianceAmount > 0}
          delta={hasBudgetVariance ? `${budgetVariancePct.toFixed(1)}%` : undefined}
          insight="Planned vs actual"
          hint={hasBudgetVariance ? `Variance ${budgetVariancePct.toFixed(1)}%` : "Variance available once budget rows exist"}
        />
      </div>
    </>
  );
}
