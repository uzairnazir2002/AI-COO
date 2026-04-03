"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api, apiFetchRaw } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { budgetSchema, budgetVarianceSchema } from "@/lib/api/schemas";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { Budget, BudgetVariance } from "@/types/domain";
import type { AlertRecalcMetadata } from "@/features/transactions/hooks";

type CreateBudgetPayload = {
  category: string;
  period_month: string;
  budget_type: "EXPENSE" | "REVENUE";
  planned_amount: string;
  notes?: string;
};

type UpdateBudgetPayload = {
  budgetId: string;
  planned_amount: string;
  notes?: string;
};

function buildBudgetQuery(orgId: string, period?: string, budgetType?: string, includeHistory?: boolean) {
  const qs = new URLSearchParams({ org_id: orgId });
  if (period) qs.set("period", period);
  if (budgetType) qs.set("budget_type", budgetType);
  if (includeHistory) qs.set("include_history", "true");
  return qs.toString();
}

function requireOrgId(orgId: string | null): string {
  if (!orgId) {
    throw new ApiError("Select an organization before managing budgets.", 400);
  }
  return orgId;
}

export function useBudgets(period: string, budgetType: "EXPENSE" | "REVENUE" | "ALL" = "ALL", includeHistory = false) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.budgets(orgId || "", period, budgetType, includeHistory),
    queryFn: async () => {
      const qs = buildBudgetQuery(orgId || "", period, budgetType === "ALL" ? undefined : budgetType, includeHistory);
      const out = await api<Budget[]>(`${apiPaths.budgets}?${qs}`);
      return out.map((row) => budgetSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useCreateBudget() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateBudgetPayload) => {
      const resolvedOrgId = requireOrgId(orgId);
      const response = await apiFetchRaw(apiPaths.budgets, {
        method: "POST",
        body: JSON.stringify({ org_id: resolvedOrgId, ...payload }),
      });
      const out = budgetSchema.parse((await response.json()) as Budget);
      const taskId = response.headers.get("X-Alert-Recalc-Task-Id");
      const status = response.headers.get("X-Alert-Recalc-Status");
      const queuedHeader = response.headers.get("X-Alert-Recalc-Queued");
      const alertRecalc: AlertRecalcMetadata | null =
        taskId && status && queuedHeader
          ? { taskId, status, queued: queuedHeader.toLowerCase() === "true" }
          : null;
      return { budget: out, alertRecalc };
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["budgets", orgId || ""] });
      await qc.invalidateQueries({ queryKey: ["budgetVariance", orgId || ""] });
    },
  });
}

export function useUpdateBudget() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateBudgetPayload) => {
      const resolvedOrgId = requireOrgId(orgId);
      const response = await apiFetchRaw(apiPaths.budgetById(payload.budgetId), {
        method: "PUT",
        body: JSON.stringify({
          org_id: resolvedOrgId,
          planned_amount: payload.planned_amount,
          notes: payload.notes,
        }),
      });
      const out = budgetSchema.parse((await response.json()) as Budget);
      const taskId = response.headers.get("X-Alert-Recalc-Task-Id");
      const status = response.headers.get("X-Alert-Recalc-Status");
      const queuedHeader = response.headers.get("X-Alert-Recalc-Queued");
      const alertRecalc: AlertRecalcMetadata | null =
        taskId && status && queuedHeader
          ? { taskId, status, queued: queuedHeader.toLowerCase() === "true" }
          : null;
      return { budget: out, alertRecalc };
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["budgets", orgId || ""] });
      await qc.invalidateQueries({ queryKey: ["budgetVariance", orgId || ""] });
    },
  });
}

export function useBudgetVariance(period: string, budgetType: "EXPENSE" | "REVENUE" | "ALL" = "ALL") {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const locationId = useAppStore((s) => s.selectedLocationId);
  return useQuery({
    queryKey: qk.budgetVariance(orgId || "", period, budgetType, locationId || ""),
    queryFn: async () => {
      const qs = new URLSearchParams({ org_id: orgId || "", period });
      if (budgetType !== "ALL") qs.set("budget_type", budgetType);
      if (locationId) qs.set("location_id", locationId);
      const out = await api<BudgetVariance>(`${apiPaths.budgetVariance}?${qs.toString()}`);
      return budgetVarianceSchema.parse(out);
    },
    enabled: Boolean(orgId),
  });
}
