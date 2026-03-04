"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { Alert } from "@/types/domain";

export function useAlerts(status: "open" | "dismissed") {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.alerts(orgId || "", status),
    queryFn: () => api<{ items: Alert[] }>(`${apiPaths.alerts}?org_id=${orgId}&status=${status}`),
    enabled: Boolean(orgId),
  });
}

export function useDismissAlert() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<{ ok: boolean }>(`${apiPaths.dismissAlert(id)}?org_id=${orgId}`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
    },
  });
}
