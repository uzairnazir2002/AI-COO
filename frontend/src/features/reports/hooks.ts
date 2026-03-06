"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { reportGenerateSchema, type ReportGenerateResponse } from "@/lib/api/schemas";
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
    mutationFn: (weekStart: string) =>
      api<ReportGenerateResponse>(`${apiPaths.generateReport}?org_id=${orgId}&week_start=${weekStart}`, {
        method: "POST",
        schema: reportGenerateSchema,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["reports"] });
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export async function fetchReportDownload(reportId: string, orgId: string) {
  const payload = await api<{ url?: string }>(`${apiPaths.downloadReport(reportId)}?org_id=${orgId}`);
  if (!payload.url) return payload;

  try {
    const parsed = new URL(payload.url);
    const publicBase =
      process.env.NEXT_PUBLIC_MINIO_PUBLIC_BASE_URL ||
      (typeof window !== "undefined" ? `${window.location.protocol}//${window.location.hostname}:9000` : "");
    if (parsed.hostname === "minio" && publicBase) {
      const target = new URL(publicBase);
      parsed.protocol = target.protocol;
      parsed.host = target.host;
      return { ...payload, url: parsed.toString() };
    }
  } catch {
    return payload;
  }

  return payload;
}
