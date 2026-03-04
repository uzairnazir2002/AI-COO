"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { Report } from "@/types/domain";

export function useReports() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.reports(orgId || ""),
    queryFn: () => api<{ items: Report[] }>(`${apiPaths.reports}?org_id=${orgId}`),
    enabled: Boolean(orgId),
  });
}

export function useGenerateReport() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (weekStart: string) => api<{ report_id: string }>(`${apiPaths.generateReport}?org_id=${orgId}&week_start=${weekStart}`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports"] }),
  });
}

export async function fetchReportDownload(reportId: string, orgId: string) {
  return api<{ url?: string }>(`${apiPaths.downloadReport(reportId)}?org_id=${orgId}`);
}
