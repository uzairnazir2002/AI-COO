"use client";

import { useMemo, useState } from "react";

import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { StatusStrip } from "@/components/layout/status-strip";
import { InlineErrorBanner } from "@/components/states/inline-error-banner";
import { RetryCard } from "@/components/states/retry-card";
import { SkeletonPanel } from "@/components/states/skeleton-panel";
import { SuccessStateCard } from "@/components/states/success-state-card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ForecastWorkspaceContainer } from "@/features/forecast/containers/forecast-workspace-container";
import { useForecast, useForecastOverride } from "@/features/forecast/hooks";
import { type ForecastAssumptions } from "@/features/forecast/panels/assumptions-panel";
import { computeChartDomain, toNumber } from "@/lib/utils/chart";
import { formatMoney } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";

type DraftRow = { revenue: string; expense: string };

export default function ForecastPage() {
  const [months, setMonths] = useState<3 | 6 | 12>(6);
  const [scenario, setScenario] = useState<"base" | "high" | "low">("base");
  const [activeTab, setActiveTab] = useState("baseline");
  const [drafts, setDrafts] = useState<Record<string, DraftRow>>({});
  const [savedOverrideMonths, setSavedOverrideMonths] = useState<string[]>([]);
  const [assumptions, setAssumptions] = useState<ForecastAssumptions>({
    plannedHireCost: "",
    plannedPurchaseCost: "",
    revenueLiftPct: "",
    expenseDeltaPct: "",
  });
  const [lastSuccess, setLastSuccess] = useState("");

  const toast = useToast();
  const experienceTier = useAppStore((s) => s.experienceTier);
  const forecast = useForecast(months);
  const override = useForecastOverride();

  const points = useMemo(() => {
    const arr = forecast.data?.scenarios[scenario] ?? [];
    return arr.map((item) => {
      const revenue = toNumber(item.revenue_pred);
      const expense = toNumber(item.expense_pred);
      const low = toNumber(item.confidence_low);
      const high = toNumber(item.confidence_high);
      return {
        ...item,
        revenue_pred: revenue,
        expense_pred: expense,
        confidence_low: low,
        confidence_high: high,
        confidence_band: Math.max(0, high - low),
        net: revenue - expense,
      };
    });
  }, [forecast.data, scenario]);

  const runwayProjection = useMemo(() => {
    let runningCash = 0;
    return points.map((point) => {
      runningCash += point.net;
      return { month: point.month, projected_cash_delta: runningCash };
    });
  }, [points]);

  const risk = points.length > 0 && points[points.length - 1].expense_pred > points[points.length - 1].revenue_pred;
  const hasVariance = points.some((point) => Math.abs(point.revenue_pred) > 0 || Math.abs(point.expense_pred) > 0 || Math.abs(point.confidence_high - point.confidence_low) > 0);
  const forecastDomain = useMemo(
    () => computeChartDomain(points.flatMap((point) => [point.revenue_pred, point.expense_pred, point.confidence_low, point.confidence_high]), 100),
    [points],
  );
  const runwayDomain = useMemo(() => computeChartDomain(runwayProjection.map((p) => p.projected_cash_delta), 100), [runwayProjection]);
  const lastPoint = points[points.length - 1];
  const expenseOverRevenue = lastPoint ? lastPoint.expense_pred - lastPoint.revenue_pred : 0;
  const assumptionsNetImpact = useMemo(() => {
    if (!lastPoint) return 0;
    const plannedHire = Number(assumptions.plannedHireCost || 0);
    const plannedPurchase = Number(assumptions.plannedPurchaseCost || 0);
    const revenueLift = Number(assumptions.revenueLiftPct || 0) / 100;
    const expenseDelta = Number(assumptions.expenseDeltaPct || 0) / 100;
    const liftedRevenue = lastPoint.revenue_pred * revenueLift;
    const raisedExpense = lastPoint.expense_pred * expenseDelta;
    return liftedRevenue - raisedExpense - plannedHire - plannedPurchase;
  }, [assumptions.expenseDeltaPct, assumptions.plannedHireCost, assumptions.plannedPurchaseCost, assumptions.revenueLiftPct, lastPoint]);

  async function saveDraft(month: string) {
    const row = drafts[month];
    if (!row) return;
    await override.mutateAsync({
      month,
      scenario: scenario.toUpperCase() as "BASE" | "HIGH" | "LOW",
      revenue_override: row.revenue.trim() ? Number(row.revenue) : undefined,
      expense_override: row.expense.trim() ? Number(row.expense) : undefined,
    });
    setSavedOverrideMonths((prev) => (prev.includes(month) ? prev : [...prev, month]));
    setDrafts((prev) => {
      const next = { ...prev };
      delete next[month];
      return next;
    });
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Forecast"
        description="Planning workspace with baseline runway, risk view, and optional advanced controls."
        actions={
          <>
            <div className="w-24">
              <Select value={String(months)} onValueChange={(value) => setMonths(Number(value) as 3 | 6 | 12)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="3">3 mo</SelectItem>
                  <SelectItem value="6">6 mo</SelectItem>
                  <SelectItem value="12">12 mo</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-32">
              <Select value={scenario} onValueChange={(value) => setScenario(value as "base" | "high" | "low")}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="base">Base</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        }
      />

      <StatusStrip
        items={[
          { label: "Scenario", value: scenario.toUpperCase(), tone: "neutral" },
          { label: "Horizon", value: `${months} months`, tone: "neutral" },
          { label: "Risk", value: risk ? "Elevated" : "Stable", tone: risk ? "warning" : "live" },
        ]}
      />

      {forecast.isLoading ? <SkeletonPanel rows={5} /> : null}

      {forecast.error ? (
        <div className="space-y-3">
          <InlineErrorBanner message={String((forecast.error as Error).message || "Unable to load forecast data.")} />
          <RetryCard message="Retry loading forecast scenarios." onRetry={() => void forecast.refetch()} />
        </div>
      ) : null}

      {lastSuccess ? (
        <SuccessStateCard
          title="Forecast overrides synced"
          description={lastSuccess.startsWith("Override saved for") ? "A forecast override was saved successfully." : lastSuccess}
        />
      ) : null}

      <ForecastWorkspaceContainer
        experienceTier={experienceTier}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        points={points}
        runwayProjection={runwayProjection}
        risk={risk}
        hasVariance={hasVariance}
        forecastLoading={forecast.isLoading}
        months={months}
        scenario={scenario}
        savedOverrideMonths={savedOverrideMonths}
        forecastDomain={forecastDomain}
        runwayDomain={runwayDomain}
        drafts={drafts}
        overridePending={override.isPending}
        onDraftRevenueChange={(month, value) =>
          setDrafts((prev) => ({ ...prev, [month]: { ...(prev[month] ?? { revenue: "", expense: "" }), revenue: value } }))
        }
        onDraftExpenseChange={(month, value) =>
          setDrafts((prev) => ({ ...prev, [month]: { ...(prev[month] ?? { revenue: "", expense: "" }), expense: value } }))
        }
        onSaveDraft={async (month) => {
          await saveDraft(month);
          setLastSuccess(`Override saved for ${month}.`);
          toast.toast({ title: `Override saved for ${month}` });
        }}
        onResetDraft={(month) => {
          setDrafts((prev) => {
            const next = { ...prev };
            delete next[month];
            return next;
          });
        }}
        onSaveAll={async () => {
          for (const month of Object.keys(drafts)) await saveDraft(month);
          setLastSuccess("All visible forecast overrides were saved.");
          toast.toast({ title: "All overrides saved" });
        }}
        onResetAll={() => setDrafts({})}
        assumptions={assumptions}
        onAssumptionsChange={setAssumptions}
        assumptionsNetImpact={assumptionsNetImpact}
        expenseOverRevenue={expenseOverRevenue}
      />
    </div>
  );
}

