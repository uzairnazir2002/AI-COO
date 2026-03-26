"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, apiFetchRaw } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import {
  inventoryForecastSchema,
  inventoryItemSchema,
  inventoryPurchaseOrderSchema,
  inventoryStockEventSchema,
} from "@/lib/api/schemas";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { InventoryForecast, InventoryItem, InventoryPurchaseOrder, InventoryStockEvent } from "@/types/domain";
import type { AlertRecalcMetadata } from "@/features/transactions/hooks";

type CreateItemPayload = {
  sku: string;
  name: string;
  unit_cost: string;
  reorder_point: string;
};

type CreateStockEventPayload = {
  item_id: string;
  event_type: "INBOUND" | "OUTBOUND" | "ADJUSTMENT";
  quantity: string;
  unit_cost?: string;
  reference?: string;
  notes?: string;
};

type CreatePurchaseOrderPayload = {
  item_id: string;
  quantity: string;
  expected_date: string;
  unit_cost?: string;
  external_ref?: string;
};

function readAlertRecalcMetadata(headers: Headers): AlertRecalcMetadata | null {
  const taskId = headers.get("X-Alert-Recalc-Task-Id");
  const status = headers.get("X-Alert-Recalc-Status");
  const queuedHeader = headers.get("X-Alert-Recalc-Queued");
  if (!taskId || !status || !queuedHeader) return null;
  return { taskId, status, queued: queuedHeader.toLowerCase() === "true" };
}

export function useInventoryItems(includeInactive = false) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const locationId = useAppStore((s) => s.selectedLocationId);
  return useQuery({
    queryKey: qk.inventoryItems(orgId || "", locationId || "", includeInactive),
    queryFn: async () => {
      const qs = new URLSearchParams({ org_id: orgId || "" });
      if (includeInactive) qs.set("include_inactive", "true");
      if (locationId) qs.set("location_id", locationId);
      const out = await api<InventoryItem[]>(`${apiPaths.inventoryItems}?${qs.toString()}`);
      return out.map((row) => inventoryItemSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useInventoryForecast(lookbackDays = 30, horizonDays = 30) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const locationId = useAppStore((s) => s.selectedLocationId);
  return useQuery({
    queryKey: qk.inventoryForecast(orgId || "", locationId || "", lookbackDays, horizonDays),
    queryFn: async () => {
      const qs = new URLSearchParams({
        org_id: orgId || "",
        lookback_days: String(lookbackDays),
        horizon_days: String(horizonDays),
      });
      if (locationId) qs.set("location_id", locationId);
      const out = await api<InventoryForecast>(`${apiPaths.inventoryForecast}?${qs.toString()}`);
      return inventoryForecastSchema.parse(out);
    },
    enabled: Boolean(orgId),
  });
}

function invalidateInventoryQueries(queryClient: ReturnType<typeof useQueryClient>, orgId: string | null) {
  queryClient.invalidateQueries({ queryKey: ["inventoryItems", orgId || ""] });
  queryClient.invalidateQueries({ queryKey: ["inventoryForecast", orgId || ""] });
  queryClient.invalidateQueries({ queryKey: ["alerts"] });
  queryClient.invalidateQueries({ queryKey: ["notifications"] });
}

export function useCreateInventoryItem() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const locationId = useAppStore((s) => s.selectedLocationId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateItemPayload) => {
      const response = await apiFetchRaw(apiPaths.inventoryItems, {
        method: "POST",
        body: JSON.stringify({
          org_id: orgId,
          location_id: locationId || undefined,
          ...payload,
        }),
      });
      const out = inventoryItemSchema.parse((await response.json()) as InventoryItem);
      return { item: out, alertRecalc: readAlertRecalcMetadata(response.headers) };
    },
    onSuccess: async () => {
      invalidateInventoryQueries(qc, orgId);
    },
  });
}

export function useCreateInventoryStockEvent() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const locationId = useAppStore((s) => s.selectedLocationId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateStockEventPayload) => {
      const response = await apiFetchRaw(apiPaths.inventoryStockEvents, {
        method: "POST",
        body: JSON.stringify({
          org_id: orgId,
          location_id: locationId || undefined,
          ...payload,
        }),
      });
      const out = inventoryStockEventSchema.parse((await response.json()) as InventoryStockEvent);
      return { event: out, alertRecalc: readAlertRecalcMetadata(response.headers) };
    },
    onSuccess: async () => {
      invalidateInventoryQueries(qc, orgId);
    },
  });
}

export function useCreateInventoryPurchaseOrder() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const locationId = useAppStore((s) => s.selectedLocationId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreatePurchaseOrderPayload) => {
      const response = await apiFetchRaw(apiPaths.inventoryPurchaseOrders, {
        method: "POST",
        body: JSON.stringify({
          org_id: orgId,
          location_id: locationId || undefined,
          ...payload,
        }),
      });
      const out = inventoryPurchaseOrderSchema.parse((await response.json()) as InventoryPurchaseOrder);
      return { purchaseOrder: out, alertRecalc: readAlertRecalcMetadata(response.headers) };
    },
    onSuccess: async () => {
      invalidateInventoryQueries(qc, orgId);
    },
  });
}
