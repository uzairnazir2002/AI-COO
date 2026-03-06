"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { getAccessToken } from "@/lib/auth/tokens";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { ImportHistoryPage, PaginatedTransactions, Transaction } from "@/types/domain";

export type TransactionFilters = {
  from?: string;
  to?: string;
  type?: string;
  category?: string;
  q?: string;
  page: number;
  page_size: number;
};

function queryString(params: Record<string, string | number | undefined>) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  return qs.toString();
}

export function useTransactions(filters: TransactionFilters) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.transactions({ ...filters, org_id: orgId || "" }),
    queryFn: async () => {
      const qs = queryString({ org_id: orgId || "", ...filters });
      return api<PaginatedTransactions>(`${apiPaths.transactions}?${qs}`);
    },
    enabled: Boolean(orgId),
  });
}

export function useCreateTransaction() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Omit<Transaction, "id">) => api<{ transaction: Transaction }>(apiPaths.transactions, { method: "POST", body: JSON.stringify(payload) }),
    onMutate: async (payload) => {
      await qc.cancelQueries({ queryKey: ["transactions"] });
      const previous = qc.getQueriesData<PaginatedTransactions>({ queryKey: ["transactions"] });
      previous.forEach(([key, value]) => {
        if (!value) return;
        qc.setQueryData<PaginatedTransactions>(key, {
          ...value,
          total: value.total + 1,
          items: [{ ...payload, id: `optimistic-${crypto.randomUUID()}` }, ...value.items],
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
    },
    meta: { orgId },
  });
}

export function useUpdateTransaction() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<Transaction> }) =>
      api<{ transaction: Transaction }>(`${apiPaths.transactionById(id)}?org_id=${orgId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
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
    },
  });
}

export function useDeleteTransaction() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api<{ ok: boolean }>(`${apiPaths.transactionById(id)}?org_id=${orgId}`, {
        method: "DELETE",
      }),
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
    },
  });
}

export async function importCsv(
  orgId: string,
  file: File,
  mapping: Record<string, string>,
  commit: boolean,
): Promise<{ import_id: string; preview: { rows: number; detected_duplicates: number }; inserted_count: number }> {
  const form = new FormData();
  form.append("org_id", orgId);
  form.append("mapping", JSON.stringify(mapping));
  form.append("commit", String(commit));
  form.append("file", file);
  return api(apiPaths.importCsv, { method: "POST", body: form });
}

export function useBulkRemapCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { org_id: string; from_category: string; to_category: string; from_date?: string; to_date?: string }) => {
      const qs = new URLSearchParams({ org_id: payload.org_id }).toString();
      return api<{ ok: boolean; updated_count: number }>(`${apiPaths.bulkRemap}?${qs}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      qc.invalidateQueries({ queryKey: ["cashflow"] });
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
  const base = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const token = getAccessToken();
  const headers = new Headers({ "X-Request-ID": crypto.randomUUID() });
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${base}${apiPaths.importErrors(importId)}?org_id=${orgId}`, {
    method: "GET",
    headers,
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(`Failed to download errors (${res.status})`);
  }
  return await res.blob();
}
