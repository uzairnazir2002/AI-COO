"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { notificationPageSchema, type NotificationPageResponse } from "@/lib/api/schemas";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";

export function useNotifications(unreadOnly = false) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.notifications(orgId || "", unreadOnly),
    queryFn: () => api<NotificationPageResponse>(`${apiPaths.notifications}?org_id=${orgId}&unread_only=${String(unreadOnly)}&page=1&page_size=30`, { schema: notificationPageSchema }),
    enabled: Boolean(orgId),
    refetchInterval: 15000,
  });
}

export function useMarkNotificationRead() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<{ ok: boolean }>(`${apiPaths.notificationRead(id)}?org_id=${orgId}`, { method: "POST" }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<{ ok: boolean; updated: number }>(`${apiPaths.notificationReadAll}?org_id=${orgId}`, { method: "POST" }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}
