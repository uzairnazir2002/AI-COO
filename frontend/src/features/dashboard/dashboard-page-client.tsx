"use client";

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, Download } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionHeader } from "@/components/common/section-header";
import { CalculationDrawer } from "@/components/drawers/calculation-drawer";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useDashboardData } from "@/features/dashboard/hooks";
import { AlertDetailDrawer } from "@/features/dashboard/panels/alert-detail-drawer";
import { BenchmarkPanel } from "@/features/dashboard/panels/benchmark-panel";
import { CashflowChartPanel } from "@/features/dashboard/panels/cashflow-chart-panel";
import { HeroStrip } from "@/features/dashboard/panels/hero-strip";
import { DashboardKpiGrid } from "@/features/dashboard/panels/kpi-grid";
import { PriorityAlertsPanel } from "@/features/dashboard/panels/priority-alerts-panel";
import { RevenueExpenseChartPanel } from "@/features/dashboard/panels/revenue-expense-chart-panel";
import { computeChartDomain, downsamplePoints, toNumber } from "@/lib/utils/chart";
import { formatCompactMoney, formatMoney, shiftDaysISO, todayISO } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";

export function DashboardPageClient() {
  const data = useDashboardData();
  const [activeAlertId, setActiveAlertId] = useState<string | null>(null);
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const cashflowGranularity = useAppStore((s) => s.cashflowGranularity);
  const setCashflowGranularity = useAppStore((s) => s.setCashflowGranularity);
  const setGlobalDateRange = useAppStore((s) => s.setGlobalDateRange);
  const selectedLocationId = useAppStore((s) => s.selectedLocationId);
  const metricForCalc = searchParams.get("metric");
  const drillPointDate = searchParams.get("point");

  const updateDashboardQuery = useCallback((next: { metric?: string | null; point?: string | null }) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next.metric !== undefined) {
      if (next.metric) params.set("metric", next.metric);
      else params.delete("metric");
    }
    if (next.point !== undefined) {
      if (next.point) params.set("point", next.point);
      else params.delete("point");
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }, [pathname, router, searchParams]);

  const pointsRaw =
    data.cashflow?.points.map((p) => ({
      ...p,
      revenue: toNumber(p.revenue),
      expense: toNumber(p.expense),
      net: toNumber(p.net),
    })) || [];
  const points = downsamplePoints(pointsRaw, 120);
  const scopedPoints = useMemo(() => {
    if (!drillPointDate) return points;
    const narrowed = points.filter((point) => point.date === drillPointDate);
    return narrowed.length > 0 ? narrowed : points;
  }, [drillPointDate, points]);
  const sparklineData = downsamplePoints(
    scopedPoints.map((point) => ({ label: point.date, value: point.net })),
    40,
  );
  const burnSpark = downsamplePoints(
    scopedPoints.map((point) => ({ label: point.date, value: point.expense - point.revenue })),
    40,
  );

  const hasData = scopedPoints.length > 0;
  const resetToLast90Days = () => {
    const to = todayISO();
    const from = shiftDaysISO(to, -89);
    setGlobalDateRange({ from, to });
  };
  const alertDetail = data.alerts.find((item) => item.id === activeAlertId) ?? null;
  const maxImpact = data.alerts.reduce((acc, alert) => {
    const value = toNumber((alert.meta as Record<string, unknown> | undefined)?.impact);
    return Math.max(acc, Math.abs(value));
  }, 0);
  const netChange = scopedPoints.length > 1 ? scopedPoints[scopedPoints.length - 1].net - scopedPoints[0].net : 0;
  const budgetPlanned = toNumber(data.budgetVariance?.totals.planned_amount);
  const budgetActual = toNumber(data.budgetVariance?.totals.actual_amount);
  const budgetVarianceAmount = toNumber(data.budgetVariance?.totals.variance_amount);
  const budgetVariancePct = budgetPlanned > 0 ? (budgetVarianceAmount / budgetPlanned) * 100 : 0;
  const revenueMtd = toNumber(data.summary?.revenue_mtd);
  const expenseMtd = toNumber(data.summary?.expenses_mtd);
  const netMarginPct = revenueMtd > 0 ? ((revenueMtd - expenseMtd) / revenueMtd) * 100 : 0;
  const hasBudgetVariance = budgetPlanned > 0 || budgetActual > 0;
  const benchmarkRows = data.locationBenchmark?.locations ?? [];
  const cashflowDomain = computeChartDomain(
    scopedPoints.flatMap((point) => [point.revenue, point.expense, point.net]),
    500,
  );
  const calculationSpecs: Record<string, { formula: string; inputs: Array<{ label: string; value: string; source?: string }> }> = {
    "Cash balance": {
      formula: "Current cash snapshot from summary service",
      inputs: [{ label: "Cash balance", value: formatMoney(data.summary?.cash_balance), source: "Summary API: cash_balance" }],
    },
    Runway: {
      formula: "Runway days = projected cash coverage under current burn profile",
      inputs: [
        { label: "Runway days", value: `${data.runway?.runway_days ?? 0} days`, source: "Runway API: runway_days" },
        { label: "Monthly burn", value: formatCompactMoney(data.summary?.burn_rate_monthly), source: "Summary API: burn_rate_monthly" },
      ],
    },
    "Burn rate": {
      formula: "Rolling monthly burn estimate",
      inputs: [{ label: "Burn rate", value: formatCompactMoney(data.summary?.burn_rate_monthly), source: "Summary API: burn_rate_monthly" }],
    },
    "Revenue MTD": {
      formula: "Sum of MTD revenue transactions in selected scope",
      inputs: [{ label: "Revenue MTD", value: formatCompactMoney(revenueMtd), source: "Summary API: revenue_mtd" }],
    },
    "Expense MTD": {
      formula: "Sum of MTD expense transactions in selected scope",
      inputs: [{ label: "Expense MTD", value: formatCompactMoney(expenseMtd), source: "Summary API: expenses_mtd" }],
    },
    "Net margin": {
      formula: "((Revenue MTD - Expense MTD) / Revenue MTD) * 100",
      inputs: [
        { label: "Revenue MTD", value: formatCompactMoney(revenueMtd), source: "Summary API: revenue_mtd" },
        { label: "Expense MTD", value: formatCompactMoney(expenseMtd), source: "Summary API: expenses_mtd" },
        { label: "Net margin", value: `${netMarginPct.toFixed(1)}%`, source: "Client formula" },
      ],
    },
  };
  const selectedCalculation = metricForCalc ? calculationSpecs[metricForCalc] : null;

  if (!data.orgId) {
    return (
      <EmptyState
        eyebrow="No organization"
        title="Select or create an organization to continue."
        description="The dashboard is fully org-scoped. Once an organization is selected, analytics, reports, and permissions all follow that context."
        actions={[{ label: "Go to organizations", href: "/app/orgs" }]}
      />
    );
  }

  if (data.error) {
    return <ErrorState description={String((data.error as Error).message || data.error)} />;
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Overview"
        title="Executive dashboard"
        description="KPIs, risk signals, cashflow movement, and AI narrative for the currently selected organization and date range."
        scopeChips={[
          `${data.from} to ${data.to}`,
          selectedLocationId ? "Location scope: filtered" : "Location scope: all",
          `Granularity: ${cashflowGranularity}`,
          drillPointDate ? `Drill point: ${drillPointDate}` : "Drill point: none",
        ]}
        actions={
          <>
            <div className="w-36">
              <Select
                value={cashflowGranularity}
                onValueChange={(value) => setCashflowGranularity(value as "day" | "week" | "month")}
              >
                <SelectTrigger className="h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="day">Daily</SelectItem>
                  <SelectItem value="week">Weekly</SelectItem>
                  <SelectItem value="month">Monthly</SelectItem>
                </SelectContent>
                </Select>
              </div>
            {drillPointDate ? (
              <Button variant="ghost" onClick={() => updateDashboardQuery({ point: null })}>
                Clear drill
              </Button>
            ) : null}
            <Button asChild variant="outline">
              <Link href="/app/reports">
                Weekly report <Download className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild>
              <Link href="/app/transactions">
                Add transaction <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </>
        }
      />

      <HeroStrip from={data.from} to={data.to} headline={data.ai?.summary_json?.headline} />

      <DashboardKpiGrid
        periodLabel={`${data.from} to ${data.to}`}
        cashBalance={data.summary?.cash_balance}
        netChange={netChange}
        runwayDays={data.runway?.runway_days}
        runwayAlert={data.runway?.alert}
        burnRateMonthly={data.summary?.burn_rate_monthly}
        revenueMtd={revenueMtd}
        expenseMtd={expenseMtd}
        netMarginPct={netMarginPct}
        sparklineData={sparklineData}
        burnSpark={burnSpark}
        budgetPlanned={budgetPlanned}
        budgetActual={budgetActual}
        budgetVarianceAmount={budgetVarianceAmount}
        budgetVariancePct={budgetVariancePct}
        hasBudgetVariance={hasBudgetVariance}
        onSelectMetric={(metric) => updateDashboardQuery({ metric })}
      />

      <div className="grid gap-4 xl:grid-cols-2">
        <CashflowChartPanel
          loading={data.loading}
          hasData={hasData}
          points={scopedPoints}
          cashflowGranularity={cashflowGranularity}
          from={data.from}
          to={data.to}
          domain={cashflowDomain}
          onResetToLast90Days={resetToLast90Days}
          selectedPointDate={drillPointDate}
          onPointSelect={(date) => updateDashboardQuery({ point: drillPointDate === date ? null : date })}
        />
        <RevenueExpenseChartPanel
          loading={data.loading}
          hasData={hasData}
          points={scopedPoints}
          cashflowGranularity={cashflowGranularity}
          from={data.from}
          to={data.to}
          domain={cashflowDomain}
          onResetToLast90Days={resetToLast90Days}
          selectedPointDate={drillPointDate}
          onPointSelect={(date) => updateDashboardQuery({ point: drillPointDate === date ? null : date })}
        />
      </div>

      <PriorityAlertsPanel
        loading={data.loading}
        alerts={data.alerts}
        maxImpact={maxImpact}
        onOpenAlert={setActiveAlertId}
        budgetThresholdAlerts={data.budgetThresholdAlerts}
        budgetThresholdPct={data.budgetThresholdPct}
        aiSummary={data.ai?.summary_json ?? null}
        aiFallbackUsed={data.ai?.fallback_used}
      />

      <BenchmarkPanel from={data.from} to={data.to} rows={benchmarkRows} selectedLocationId={selectedLocationId} />

      <AlertDetailDrawer alert={alertDetail} onClose={() => setActiveAlertId(null)} />
      {selectedCalculation ? (
        <CalculationDrawer
          open={Boolean(metricForCalc)}
          onClose={() => updateDashboardQuery({ metric: null })}
          metricLabel={metricForCalc || "Metric"}
          formula={selectedCalculation.formula}
          inputs={selectedCalculation.inputs}
        />
      ) : null}
    </div>
  );
}
