"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { Forecast } from "@/types/domain";

export function useForecast(months: 3 | 6 | 12) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.forecast(orgId || "", months),
    queryFn: () => api<Forecast>(`${apiPaths.forecast}?org_id=${orgId}&months=${months}`),
    enabled: Boolean(orgId),
  });
}

export function useForecastOverride() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { month: string; scenario: "BASE" | "HIGH" | "LOW"; revenue_override?: number; expense_override?: number }) =>
      api<{ ok: boolean }>(apiPaths.forecastOverride, {
        method: "POST",
        body: JSON.stringify({ org_id: orgId, ...payload }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["forecast"] }),
  });
}
