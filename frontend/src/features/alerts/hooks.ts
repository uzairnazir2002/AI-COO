"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { Alert, AlertHistoryItem } from "@/types/domain";

function requireOrgId(orgId: string | null): string {
  if (!orgId) {
    throw new ApiError("Select an organization before managing alerts.", 400);
  }
  return orgId;
}

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
    mutationFn: (id: string) => {
      const resolvedOrgId = requireOrgId(orgId);
      return api<{ ok: boolean }>(`${apiPaths.dismissAlert(id)}?org_id=${resolvedOrgId}`, { method: "POST" });
    },
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
    mutationFn: ({ id, assigneeUserId }: { id: string; assigneeUserId: string | null }) => {
      const resolvedOrgId = requireOrgId(orgId);
      return api<{ ok: boolean; alert: Alert }>(apiPaths.assignAlert(id), {
        method: "POST",
        body: JSON.stringify({ org_id: resolvedOrgId, assignee_user_id: assigneeUserId }),
      });
    },
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
    mutationFn: (id: string) => {
      const resolvedOrgId = requireOrgId(orgId);
      return api<{ ok: boolean; alert: Alert }>(apiPaths.acknowledgeAlert(id), {
        method: "POST",
        body: JSON.stringify({ org_id: resolvedOrgId }),
      });
    },
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
