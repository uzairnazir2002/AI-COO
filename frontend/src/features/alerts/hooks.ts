"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { Alert, AlertHistoryItem } from "@/types/domain";

export function useAlerts(status: "open" | "dismissed", assigneeUserId?: string, enabled = true) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const selectedLocationId = useAppStore((s) => s.selectedLocationId);
  const assigneeQuery = assigneeUserId ? `&assignee_user_id=${assigneeUserId}` : "";
  const locationQuery = selectedLocationId ? `&location_id=${selectedLocationId}` : "";
  return useQuery({
    queryKey: qk.alerts(orgId || "", status, assigneeUserId || "", selectedLocationId || ""),
    queryFn: () =>
      api<{ items: Alert[] }>(`${apiPaths.alerts}?org_id=${orgId}&status=${status}${assigneeQuery}${locationQuery}`),
    enabled: Boolean(orgId) && enabled,
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

export function useAssignAlert() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, assigneeUserId }: { id: string; assigneeUserId: string | null }) =>
      api<{ ok: boolean; alert: Alert }>(apiPaths.assignAlert(id), {
        method: "POST",
        body: JSON.stringify({ org_id: orgId, assignee_user_id: assigneeUserId }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
    },
  });
}

export function useAcknowledgeAlert() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api<{ ok: boolean; alert: Alert }>(apiPaths.acknowledgeAlert(id), {
        method: "POST",
        body: JSON.stringify({ org_id: orgId }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
    },
  });
}

export function useAlertHistory(alertId: string | null) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: ["alertHistory", orgId || "", alertId || ""],
    queryFn: () => api<{ items: AlertHistoryItem[] }>(`${apiPaths.alertHistory(alertId || "")}?org_id=${orgId}`),
    enabled: Boolean(orgId && alertId),
  });
}
