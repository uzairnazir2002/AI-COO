"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { Org } from "@/types/domain";

export function useOrgs() {
  return useQuery({
    queryKey: qk.orgs,
    queryFn: () => api<Org[]>(apiPaths.orgs),
  });
}

export function useCreateOrg() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api<{ org_id: string; name: string }>(apiPaths.orgs, {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: qk.orgs });
      await queryClient.invalidateQueries({ queryKey: qk.me });
    },
  });
}

export function useSelectedOrgRole() {
  const selected = useAppStore((s) => s.selectedOrgId);
  const orgs = useAppStore((s) => s.orgs);
  return orgs.find((o) => o.org_id === selected)?.role;
}
