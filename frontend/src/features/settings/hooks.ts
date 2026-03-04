"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { Member, OrgSettings, Role } from "@/types/domain";

export function useOrgMembers() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  return useQuery({
    queryKey: qk.members(orgId || ""),
    queryFn: () => api<Member[]>(apiPaths.members(orgId || "")),
    enabled: Boolean(orgId && role === "OWNER"),
  });
}

export function useInviteMember() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { email: string; role: Role }) =>
      api<{ ok: boolean; invite_token?: string }>(apiPaths.invite(orgId || ""), {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.members(orgId || "") }),
  });
}

export function useOrgSettings() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.settings(orgId || ""),
    queryFn: () => api<OrgSettings>(apiPaths.settings(orgId || "")),
    enabled: Boolean(orgId),
  });
}

export function useUpdateOrgSettings() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<OrgSettings>) =>
      api<OrgSettings>(apiPaths.settings(orgId || ""), {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.settings(orgId || "") }),
  });
}
