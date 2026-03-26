"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { aiSummarySchema, budgetVarianceSchema, locationBenchmarkSchema, summarySchema } from "@/lib/api/schemas";
import type {
  AiSummaryResponse,
  BudgetVarianceResponse,
  LocationBenchmarkResponse,
  SummaryResponse,
} from "@/lib/api/schemas";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { Alert, Cashflow, Runway } from "@/types/domain";

type PersistedBudgetThresholdAlert = {
  alertId: string;
  category: string;
  periodMonth: string | null;
  variancePct: number;
  thresholdPct: number | null;
  plannedAmount: number;
  actualAmount: number;
  varianceAmount: number;
};

function toNumber(value: unknown): number {
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function parsePersistedBudgetThresholdAlert(alert: Alert): PersistedBudgetThresholdAlert | null {
  if (alert.kind !== "PROFIT_LEAK") return null;
  const meta = (alert.meta || {}) as Record<string, unknown>;
  if (String(meta.subkind || "").toUpperCase() !== "BUDGET_THRESHOLD") return null;

  return {
    alertId: alert.id,
    category: String(meta.category || "Uncategorized"),
    periodMonth: meta.period_month ? String(meta.period_month) : null,
    variancePct: toNumber(meta.variance_pct),
    thresholdPct:
      meta.threshold_pct === undefined || meta.threshold_pct === null ? null : toNumber(meta.threshold_pct),
    plannedAmount: toNumber(meta.planned_amount),
    actualAmount: toNumber(meta.actual_amount),
    varianceAmount: toNumber(meta.variance_amount),
  };
}

export function useDashboardData() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const selectedLocationId = useAppStore((s) => s.selectedLocationId);
  const range = useAppStore((s) => s.globalDateRange);
  const from = range.from;
  const to = range.to;

  const enabled = Boolean(orgId);
  const budgetPeriodMonth = `${to.slice(0, 7)}-01`;
  const locationQuery = selectedLocationId ? `&location_id=${selectedLocationId}` : "";

  const summary = useQuery({
    queryKey: qk.summary(orgId || "", from, to, selectedLocationId || ""),
    queryFn: () =>
      api<SummaryResponse>(apiPaths.summary + `?org_id=${orgId}&from=${from}&to=${to}${locationQuery}`, {
        schema: summarySchema,
      }),
    enabled,
  });

  const cashflowGranularity = useAppStore((s) => s.cashflowGranularity ?? "week");

  const cashflow = useQuery({
    queryKey: qk.cashflow(orgId || "", from, to, cashflowGranularity, selectedLocationId || ""),
    queryFn: () =>
      api<Cashflow>(
        apiPaths.cashflow + `?org_id=${orgId}&from=${from}&to=${to}&granularity=${cashflowGranularity}${locationQuery}`,
      ),
    enabled,
  });

  const runway = useQuery({
    queryKey: qk.runway(orgId || "", 6, true, selectedLocationId || ""),
    queryFn: () =>
      api<Runway>(apiPaths.runway + `?org_id=${orgId}&lookback_months=6&conservative=true${locationQuery}`),
    enabled,
  });

  const alerts = useQuery({
    queryKey: qk.alerts(orgId || "", "open", "", selectedLocationId || ""),
    queryFn: () => api<{ items: Alert[] }>(apiPaths.alerts + `?org_id=${orgId}&status=open${locationQuery}`),
    enabled,
  });

  const ai = useQuery({
    queryKey: ["ai", orgId, from, to],
    queryFn: () =>
      api<AiSummaryResponse>(apiPaths.aiSummary, {
        method: "POST",
        body: JSON.stringify({ org_id: orgId, from, to }),
        schema: aiSummarySchema,
      }),
    enabled,
  });

  const budgetVariance = useQuery({
    queryKey: qk.budgetVariance(orgId || "", budgetPeriodMonth, "EXPENSE", selectedLocationId || ""),
    queryFn: () =>
      api<BudgetVarianceResponse>(
        `${apiPaths.budgetVariance}?org_id=${orgId}&period=${budgetPeriodMonth}&budget_type=EXPENSE${locationQuery}`,
        { schema: budgetVarianceSchema },
      ),
    enabled,
  });

  const locationBenchmark = useQuery({
    queryKey: qk.locationBenchmark(orgId || "", from, to),
    queryFn: () =>
      api<LocationBenchmarkResponse>(`${apiPaths.locationBenchmark}?org_id=${orgId}&from=${from}&to=${to}`, {
        schema: locationBenchmarkSchema,
      }),
    enabled,
  });

  const budgetThresholdAlerts = useMemo(() => {
    return (alerts.data?.items || [])
      .map((item) => parsePersistedBudgetThresholdAlert(item))
      .filter((item): item is PersistedBudgetThresholdAlert => item !== null);
  }, [alerts.data]);

  const nonBudgetAlerts = useMemo(
    () => (alerts.data?.items || []).filter((item) => parsePersistedBudgetThresholdAlert(item) === null),
    [alerts.data],
  );

  const budgetThresholdPct = useMemo(() => {
    if (budgetThresholdAlerts.length === 0) return null;
    const thresholds = budgetThresholdAlerts
      .map((item) => item.thresholdPct)
      .filter((value): value is number => value !== null);
    if (thresholds.length === 0) return null;
    return thresholds[0];
  }, [budgetThresholdAlerts]);

  const loading = [summary, cashflow, runway, alerts, ai, budgetVariance, locationBenchmark].some((q) => q.isLoading);
  const error = [summary, cashflow, runway, alerts, ai, budgetVariance, locationBenchmark].find((q) => q.error)?.error;

  return useMemo(
    () => ({
      orgId,
      from,
      to,
      cashflowGranularity,
      summary: summary.data,
      cashflow: cashflow.data,
      runway: runway.data,
      alerts: nonBudgetAlerts,
      ai: ai.data,
      budgetVariance: budgetVariance.data,
      locationBenchmark: locationBenchmark.data,
      budgetThresholdPct,
      budgetThresholdAlerts,
      loading,
      error,
    }),
    [
      orgId,
      from,
      to,
      cashflowGranularity,
      summary.data,
      cashflow.data,
      runway.data,
      nonBudgetAlerts,
      ai.data,
      budgetVariance.data,
      locationBenchmark.data,
      budgetThresholdPct,
      budgetThresholdAlerts,
      loading,
      error,
    ],
  );
}
