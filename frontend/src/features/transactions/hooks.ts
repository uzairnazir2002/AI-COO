"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api, apiFetchRaw } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { ImportHistoryPage, ImportMappingProfile, PaginatedTransactions, Transaction } from "@/types/domain";

export type TransactionFilters = {
  from?: string;
  to?: string;
  type?: string;
  category?: string;
  q?: string;
  location_id?: string;
  page: number;
  page_size: number;
};

export type AlertRecalcMetadata = {
  taskId: string;
  status: string;
  queued: boolean;
};

function readAlertRecalcMetadata(headers: Headers): AlertRecalcMetadata | null {
  const taskId = headers.get("X-Alert-Recalc-Task-Id");
  const status = headers.get("X-Alert-Recalc-Status");
  const queuedHeader = headers.get("X-Alert-Recalc-Queued");
  if (!taskId || !status || !queuedHeader) return null;
  return {
    taskId,
    status,
    queued: queuedHeader.toLowerCase() === "true",
  };
}

function queryString(params: Record<string, string | number | undefined>) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return qs.toString();
}

export function useTransactions(filters: TransactionFilters) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const selectedLocationId = useAppStore((s) => s.selectedLocationId);
  const locationId = filters.location_id ?? selectedLocationId ?? undefined;
  return useQuery({
    queryKey: qk.transactions({ ...filters, location_id: locationId, org_id: orgId || "" }),
    queryFn: async () => {
      const qs = queryString({ org_id: orgId || "", ...filters, location_id: locationId });
      return api<PaginatedTransactions>(`${apiPaths.transactions}?${qs}`);
    },
    enabled: Boolean(orgId),
  });
}

export function useCreateTransaction() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Omit<Transaction, "id">) => {
      const resolvedOrg = orgId || payload.org_id;
      if (!resolvedOrg) {
        throw new ApiError("Select an organization before creating a transaction.", 400);
      }
      if (orgId && payload.org_id && payload.org_id !== orgId) {
        throw new ApiError(
          "Transaction targets a different organization than the one selected. Refresh the page and try again.",
          400,
        );
      }
      const body: Omit<Transaction, "id"> = {
        ...payload,
        org_id: orgId || payload.org_id || resolvedOrg,
      };
      const response = await apiFetchRaw(apiPaths.transactions, { method: "POST", body: JSON.stringify(body) });
      const json = (await response.json()) as { transaction: Transaction };
      return { transaction: json.transaction, alertRecalc: readAlertRecalcMetadata(response.headers) };
    },
    onMutate: async (payload) => {
      const resolvedOrg = orgId || payload.org_id;
      const optimisticRow = {
        ...payload,
        org_id: orgId || payload.org_id || resolvedOrg || "",
        id: `optimistic-${crypto.randomUUID()}`,
      };
      await qc.cancelQueries({ queryKey: ["transactions"] });
      const previous = qc.getQueriesData<PaginatedTransactions>({ queryKey: ["transactions"] });
      previous.forEach(([key, value]) => {
        if (!value) return;
        qc.setQueryData<PaginatedTransactions>(key, {
          ...value,
          total: value.total + 1,
          items: [optimisticRow as Transaction, ...value.items],
        });
      });
      return { previous };
    },
    onError: (_error, _payload, context) => {
      context?.previous.forEach(([key, value]) => qc.setQueryData(key, value));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      qc.invalidateQueries({ queryKey: ["cashflow"] });
      qc.invalidateQueries({ queryKey: ["runway"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["locationBenchmark"] });
    },
    meta: { orgId },
  });
}

export function useUpdateTransaction() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Partial<Transaction> }) => {
      if (!orgId) {
        throw new ApiError("Select an organization before updating a transaction.", 400);
      }
      const response = await apiFetchRaw(`${apiPaths.transactionById(id)}?org_id=${orgId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      const json = (await response.json()) as { transaction: Transaction };
      return { transaction: json.transaction, alertRecalc: readAlertRecalcMetadata(response.headers) };
    },
    onMutate: async ({ id, payload }) => {
      await qc.cancelQueries({ queryKey: ["transactions"] });
      const previous = qc.getQueriesData<PaginatedTransactions>({ queryKey: ["transactions"] });
      previous.forEach(([key, value]) => {
        if (!value) return;
        qc.setQueryData<PaginatedTransactions>(key, {
          ...value,
          items: value.items.map((item) => (item.id === id ? { ...item, ...payload } : item)),
        });
      });
      return { previous };
    },
    onError: (_error, _payload, context) => {
      context?.previous.forEach(([key, value]) => qc.setQueryData(key, value));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      qc.invalidateQueries({ queryKey: ["cashflow"] });
      qc.invalidateQueries({ queryKey: ["runway"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["locationBenchmark"] });
    },
  });
}

export function useDeleteTransaction() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      if (!orgId) {
        throw new ApiError("Select an organization before deleting a transaction.", 400);
      }
      const response = await apiFetchRaw(`${apiPaths.transactionById(id)}?org_id=${orgId}`, {
        method: "DELETE",
      });
      const json = (await response.json()) as { ok: boolean };
      return { ok: json.ok, alertRecalc: readAlertRecalcMetadata(response.headers) };
    },
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ["transactions"] });
      const previous = qc.getQueriesData<PaginatedTransactions>({ queryKey: ["transactions"] });
      previous.forEach(([key, value]) => {
        if (!value) return;
        qc.setQueryData<PaginatedTransactions>(key, {
          ...value,
          total: Math.max(0, value.total - 1),
          items: value.items.filter((item) => item.id !== id),
        });
      });
      return { previous };
    },
    onError: (_error, _payload, context) => {
      context?.previous.forEach(([key, value]) => qc.setQueryData(key, value));
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      qc.invalidateQueries({ queryKey: ["cashflow"] });
      qc.invalidateQueries({ queryKey: ["runway"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["locationBenchmark"] });
    },
  });
}

export async function importCsv(
  orgId: string,
  file: File,
  mapping: Record<string, string> | undefined,
  commit: boolean,
  profileId?: string,
): Promise<{
  import_id: string;
  preview: { rows: number; detected_duplicates: number };
  inserted_count: number;
  mapping_profile_id?: string | null;
  alertRecalc: AlertRecalcMetadata | null;
}> {
  const form = new FormData();
  form.append("org_id", orgId);
  if (mapping) form.append("mapping", JSON.stringify(mapping));
  if (profileId) form.append("profile_id", profileId);
  form.append("commit", String(commit));
  form.append("file", file);
  const response = await apiFetchRaw(apiPaths.importCsv, { method: "POST", body: form });
  const json = (await response.json()) as {
    import_id: string;
    preview: { rows: number; detected_duplicates: number };
    inserted_count: number;
    mapping_profile_id?: string | null;
  };
  return {
    ...json,
    alertRecalc: readAlertRecalcMetadata(response.headers),
  };
}

export function useImportProfiles() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: ["import-profiles", orgId],
    queryFn: () => api<ImportMappingProfile[]>(`${apiPaths.importProfiles}?org_id=${orgId}`),
    enabled: Boolean(orgId),
  });
}

export function useCreateImportProfile() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; column_map: Record<string, string>; shared?: boolean }) =>
      api<ImportMappingProfile>(apiPaths.importProfiles, {
        method: "POST",
        body: JSON.stringify({ org_id: orgId, name: payload.name, column_map: payload.column_map, shared: payload.shared ?? false }),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["import-profiles", orgId] });
    },
  });
}

export function useUpdateImportProfile() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { profile_id: string; name?: string; column_map?: Record<string, string>; shared?: boolean }) =>
      api<ImportMappingProfile>(apiPaths.importProfileById(payload.profile_id), {
        method: "PUT",
        body: JSON.stringify({ org_id: orgId, name: payload.name, column_map: payload.column_map, shared: payload.shared }),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["import-profiles", orgId] });
    },
  });
}

export function useDeleteImportProfile() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (profileId: string) =>
      api<{ ok: boolean }>(`${apiPaths.importProfileById(profileId)}?org_id=${orgId}`, { method: "DELETE" }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["import-profiles", orgId] });
    },
  });
}

export function useBulkRemapCategory() {
  const selectedOrgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { org_id: string; from_category: string; to_category: string; from_date?: string; to_date?: string }) => {
      const canonicalOrg = selectedOrgId || payload.org_id;
      if (!canonicalOrg) {
        throw new ApiError("Select an organization before remapping categories.", 400);
      }
      if (selectedOrgId && payload.org_id && payload.org_id !== selectedOrgId) {
        throw new ApiError(
          "Remap must apply to the selected organization. Refresh the page if this persists.",
          400,
        );
      }
      const qs = new URLSearchParams({ org_id: canonicalOrg }).toString();
      const body = { ...payload, org_id: canonicalOrg };
      const response = await apiFetchRaw(`${apiPaths.bulkRemap}?${qs}`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      const json = (await response.json()) as { ok: boolean; updated_count: number };
      return { ...json, alertRecalc: readAlertRecalcMetadata(response.headers) };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      qc.invalidateQueries({ queryKey: ["cashflow"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["locationBenchmark"] });
    },
  });
}

export function useImportHistory(page: number, pageSize: number) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.imports(orgId || "", page, pageSize),
    queryFn: async () => {
      const qs = queryString({ org_id: orgId || "", page, page_size: pageSize });
      return api<ImportHistoryPage>(`${apiPaths.imports}?${qs}`);
    },
    enabled: Boolean(orgId),
  });
}

export async function downloadImportErrors(importId: string, orgId: string): Promise<Blob> {
  const response = await apiFetchRaw(`${apiPaths.importErrors(importId)}?org_id=${orgId}`);
  return await response.blob();
}
