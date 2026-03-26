"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { Location } from "@/types/domain";

type LocationInput = {
  name: string;
  code?: string | null;
  is_active?: boolean;
};

type LocationUpdateInput = {
  name?: string;
  code?: string | null;
  is_active?: boolean;
};

export function useLocations(options?: { includeInactive?: boolean }) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const includeInactive = options?.includeInactive ?? false;
  return useQuery({
    queryKey: qk.locations(orgId || "", includeInactive),
    queryFn: () =>
      api<Location[]>(
        `${apiPaths.locations}?org_id=${orgId}&include_inactive=${includeInactive ? "true" : "false"}`,
      ),
    enabled: Boolean(orgId),
  });
}

export function useCreateLocation() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: LocationInput) =>
      api<Location>(apiPaths.locations, {
        method: "POST",
        body: JSON.stringify({
          org_id: orgId,
          name: payload.name,
          code: payload.code || null,
          is_active: payload.is_active ?? true,
        }),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["locations"] });
    },
  });
}

export function useUpdateLocation() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: LocationUpdateInput & { id: string }) =>
      api<Location>(apiPaths.locationById(id), {
        method: "PUT",
        body: JSON.stringify({
          org_id: orgId,
          name: payload.name,
          code: payload.code === undefined ? undefined : payload.code || null,
          is_active: payload.is_active,
        }),
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["locations"] });
    },
  });
}

export function useDeactivateLocation() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api<{ ok: boolean }>(`${apiPaths.locationById(id)}?org_id=${orgId}`, { method: "DELETE" }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["locations"] });
    },
  });
}
