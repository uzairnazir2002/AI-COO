"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { jobPageSchema, outboxPageSchema, systemStatusSchema, type JobPageResponse, type OutboxPageResponse, type SystemStatusResponse } from "@/lib/api/schemas";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { AdminRecomputeResult, AnalyticsRecomputeResult } from "@/types/domain";

export type JobFilters = {
  status?: string;
  task_name?: string;
  page: number;
  page_size: number;
};

export type OutboxFilters = {
  status?: string;
  event_type?: string;
  page: number;
  page_size: number;
};

function queryString(params: Record<string, string | number | undefined>) {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") qs.set(key, String(value));
  }
  return qs.toString();
}

export function useJobs(filters: JobFilters) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.jobs(orgId || "", { ...filters, org_id: orgId || "" }),
    queryFn: () => {
      const qs = queryString({ org_id: orgId || "", ...filters });
      return api<JobPageResponse>(`${apiPaths.jobs}?${qs}`, { schema: jobPageSchema });
    },
    enabled: Boolean(orgId),
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasActive = data?.items?.some((item) => ["PENDING", "RUNNING", "RETRYING"].includes(item.status));
      return hasActive ? 5000 : 15000;
    },
  });
}

export function useAnalyticsRecompute() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api<AnalyticsRecomputeResult>(`${apiPaths.recompute}?org_id=${orgId}`, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      await queryClient.invalidateQueries({ queryKey: ["alerts"] });
      await queryClient.invalidateQueries({ queryKey: ["forecast"] });
    },
  });
}

export function useAdminRecompute() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api<AdminRecomputeResult>(`${apiPaths.adminRecompute}?org_id=${orgId}`, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      await queryClient.invalidateQueries({ queryKey: ["summary"] });
      await queryClient.invalidateQueries({ queryKey: ["alerts"] });
      await queryClient.invalidateQueries({ queryKey: ["forecast"] });
      await queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}

export function useOutbox(filters: OutboxFilters) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.outbox(orgId || "", { ...filters, org_id: orgId || "" }),
    queryFn: () => {
      const qs = queryString({ org_id: orgId || "", ...filters });
      return api<OutboxPageResponse>(`${apiPaths.adminOutbox}?${qs}`, { schema: outboxPageSchema });
    },
    enabled: Boolean(orgId),
    refetchInterval: 15000,
  });
}

export function useSystemStatus() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.systemStatus(orgId || ""),
    queryFn: () => api<SystemStatusResponse>(`${apiPaths.adminSystemStatus}?org_id=${orgId}`, { schema: systemStatusSchema }),
    enabled: Boolean(orgId),
    refetchInterval: 30000,
  });
}

export function useRetryOutboxEvent() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) =>
      api<{ ok: boolean; id: string; status: string }>(`${apiPaths.adminOutboxRetry(eventId)}?org_id=${orgId}`, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["outbox"] });
      await queryClient.invalidateQueries({ queryKey: ["system-status"] });
    },
  });
}

export function useRetryJob() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => api<{ ok: boolean; job_id: string; status: string; new_task_id?: string }>(`${apiPaths.jobRetry(jobId)}?org_id=${orgId}`, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useCancelJob() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => api<{ ok: boolean; job_id: string; status: string }>(`${apiPaths.jobCancel(jobId)}?org_id=${orgId}`, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function usePauseSchedule() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api<{ ok: boolean; name: string; paused: boolean }>(`${apiPaths.adminSchedulePause(name)}?org_id=${orgId}`, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["systemStatus"] });
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useResumeSchedule() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api<{ ok: boolean; name: string; paused: boolean }>(`${apiPaths.adminScheduleResume(name)}?org_id=${orgId}`, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["systemStatus"] });
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useRunSchedule() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api<{ ok: boolean; name: string; task_id: string }>(`${apiPaths.adminScheduleRun(name)}?org_id=${orgId}`, { method: "POST" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["systemStatus"] });
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}
