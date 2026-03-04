"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { PaginatedTransactions, Transaction } from "@/types/domain";

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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
  });
}
