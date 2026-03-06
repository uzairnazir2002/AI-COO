"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { billingUrlSchema } from "@/lib/api/schemas";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { BillingCheckoutResult, BillingPortalResult, Member, OrgBilling, OrgSettings, PlanUsage, Role } from "@/types/domain";

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

export function usePlanUsage() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.planUsage(orgId || ""),
    queryFn: () => api<PlanUsage>(apiPaths.planUsage(orgId || "")),
    enabled: Boolean(orgId),
  });
}

export function useOrgBilling() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  return useQuery({
    queryKey: qk.billing(orgId || ""),
    queryFn: () => api<OrgBilling>(apiPaths.billing(orgId || "")),
    enabled: Boolean(orgId && role === "OWNER"),
  });
}

export function useUpdateOrgBilling() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<OrgBilling>) =>
      api<OrgBilling>(apiPaths.billing(orgId || ""), {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.billing(orgId || "") }),
  });
}

export function useBillingCheckout() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useMutation({
    mutationFn: (payload: { price_id: string; success_url: string; cancel_url: string }) =>
      api<BillingCheckoutResult>(apiPaths.billingCheckout(orgId || ""), {
        method: "POST",
        body: JSON.stringify(payload),
        schema: billingUrlSchema,
      }),
  });
}

export function useBillingPortal() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useMutation({
    mutationFn: (payload: { return_url: string }) =>
      api<BillingPortalResult>(apiPaths.billingPortal(orgId || ""), {
        method: "POST",
        body: JSON.stringify(payload),
        schema: billingUrlSchema,
      }),
  });
}
