"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { aiSummarySchema, summarySchema } from "@/lib/api/schemas";
import type { AiSummaryResponse, SummaryResponse } from "@/lib/api/schemas";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { Alert, Cashflow, Runway } from "@/types/domain";

export function useDashboardData() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const range = useAppStore((s) => s.globalDateRange);
  const from = range.from;
  const to = range.to;

  const enabled = Boolean(orgId);

  const summary = useQuery({
    queryKey: qk.summary(orgId || "", from, to),
    queryFn: () =>
      api<SummaryResponse>(apiPaths.summary + `?org_id=${orgId}&from=${from}&to=${to}`, { schema: summarySchema }),
    enabled,
  });

  const cashflowGranularity = useAppStore((s) => s.cashflowGranularity ?? "week");

  const cashflow = useQuery({
    queryKey: qk.cashflow(orgId || "", from, to, cashflowGranularity),
    queryFn: () =>
      api<Cashflow>(apiPaths.cashflow + `?org_id=${orgId}&from=${from}&to=${to}&granularity=${cashflowGranularity}`),
    enabled,
  });

  const runway = useQuery({
    queryKey: qk.runway(orgId || "", 6, true),
    queryFn: () => api<Runway>(apiPaths.runway + `?org_id=${orgId}&lookback_months=6&conservative=true`),
    enabled,
  });

  const alerts = useQuery({
    queryKey: qk.alerts(orgId || "", "open"),
    queryFn: () => api<{ items: Alert[] }>(apiPaths.alerts + `?org_id=${orgId}&status=open`),
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

  const loading = [summary, cashflow, runway, alerts, ai].some((q) => q.isLoading);
  const error = [summary, cashflow, runway, alerts, ai].find((q) => q.error)?.error;

  return useMemo(
    () => ({
      orgId,
      from,
      to,
      cashflowGranularity,
      summary: summary.data,
      cashflow: cashflow.data,
      runway: runway.data,
      alerts: alerts.data?.items || [],
      ai: ai.data,
      loading,
      error,
    }),
    [orgId, from, to, cashflowGranularity, summary.data, cashflow.data, runway.data, alerts.data, ai.data, loading, error],
  );
}
