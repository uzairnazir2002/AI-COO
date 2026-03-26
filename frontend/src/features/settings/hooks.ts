"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { getRefreshToken } from "@/lib/auth/tokens";
import { apiPaths } from "@/lib/api/endpoints";
import { billingUrlSchema, deletionRequestListSchema, paymentReconciliationSchema } from "@/lib/api/schemas";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type {
  AuthSession,
  BillingCheckoutResult,
  BillingPortalResult,
  BankConnection,
  DeletionRequestResult,
  DeletionRequestList,
  Member,
  MfaStatus,
  OrgBilling,
  OrgSettings,
  PaymentConnection,
  PaymentReconciliation,
  PlaidLinkTokenResult,
  PlanUsage,
  Role,
  StripeConnectResult,
} from "@/types/domain";

type SensitiveAuthPayload = {
  reauthToken?: string;
};

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
    mutationFn: (payload: { email: string; role: Role } & SensitiveAuthPayload) =>
      api<{ ok: boolean; invite_token?: string }>(apiPaths.invite(orgId || ""), {
        method: "POST",
        body: JSON.stringify({ email: payload.email, role: payload.role }),
        headers: payload.reauthToken ? { "X-Reauth-Token": payload.reauthToken } : undefined,
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
    mutationFn: (payload: Partial<OrgSettings> & SensitiveAuthPayload) =>
      api<OrgSettings>(apiPaths.settings(orgId || ""), {
        method: "PUT",
        body: JSON.stringify({
          starting_cash: payload.starting_cash,
          runway_alert_threshold_days: payload.runway_alert_threshold_days,
          vendor_concentration_threshold_pct: payload.vendor_concentration_threshold_pct,
          budget_variance_alert_threshold_pct: payload.budget_variance_alert_threshold_pct,
          misc_growth_multiplier: payload.misc_growth_multiplier,
          anomaly_spike_multiplier: payload.anomaly_spike_multiplier,
          owner_mfa_required: payload.owner_mfa_required,
          owner_session_max_minutes: payload.owner_session_max_minutes,
          sensitive_action_reauth_minutes: payload.sensitive_action_reauth_minutes,
        }),
        headers: payload.reauthToken ? { "X-Reauth-Token": payload.reauthToken } : undefined,
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

export function useBankConnections() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.bankConnections(orgId || ""),
    queryFn: () => api<BankConnection[]>(`${apiPaths.bankConnections}?org_id=${orgId}`),
    enabled: Boolean(orgId),
  });
}

export function usePlaidLinkToken() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useMutation({
    mutationFn: () =>
      api<PlaidLinkTokenResult>(apiPaths.plaidLinkToken, {
        method: "POST",
        body: JSON.stringify({ org_id: orgId }),
      }),
  });
}

export function usePlaidExchange() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { publicToken: string; institutionName?: string }) =>
      api<{ connection: BankConnection }>(apiPaths.plaidExchange, {
        method: "POST",
        body: JSON.stringify({
          org_id: orgId,
          public_token: payload.publicToken,
          institution_name: payload.institutionName,
        }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.bankConnections(orgId || "") }),
  });
}

export function useSyncBankConnection() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: string) =>
      api<{ job_id: string; status: string; connection_id: string }>(
        `${apiPaths.bankConnectionSync(connectionId)}?org_id=${orgId}`,
        { method: "POST" },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.jobs(orgId || "", {}) }),
  });
}

export function useDeleteBankConnection() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: string) =>
      api<{ ok: boolean }>(`${apiPaths.bankConnectionDelete(connectionId)}?org_id=${orgId}`, {
        method: "DELETE",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.bankConnections(orgId || "") }),
  });
}

export function usePaymentConnections(provider: string = "STRIPE") {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.paymentConnections(orgId || "", provider),
    queryFn: () =>
      api<PaymentConnection[]>(
        `${apiPaths.paymentConnections}?org_id=${orgId}&provider=${encodeURIComponent(provider)}`,
      ),
    enabled: Boolean(orgId),
  });
}

export function useStripeConnect() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { providerAccountId?: string; accountLabel?: string }) =>
      api<StripeConnectResult>(apiPaths.stripeConnect, {
        method: "POST",
        body: JSON.stringify({
          org_id: orgId,
          provider_account_id: payload.providerAccountId || null,
          account_label: payload.accountLabel || null,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.paymentConnections(orgId || "", "STRIPE") });
      void qc.invalidateQueries({ queryKey: ["paymentReconciliation", orgId || ""] });
    },
  });
}

type ReconciliationRange = {
  dateFrom: string;
  dateTo: string;
};

export function usePaymentReconciliation(range?: ReconciliationRange) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const today = new Date();
  const defaultTo = today.toISOString().slice(0, 10);
  const defaultFrom = new Date(today.getTime() - 29 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const dateFrom = range?.dateFrom || defaultFrom;
  const dateTo = range?.dateTo || defaultTo;
  return useQuery({
    queryKey: qk.paymentReconciliation(orgId || "", "STRIPE", dateFrom, dateTo),
    queryFn: () =>
      api<PaymentReconciliation>(
        `${apiPaths.paymentReconciliation}?org_id=${orgId}&provider=STRIPE&date_from=${encodeURIComponent(dateFrom)}&date_to=${encodeURIComponent(dateTo)}`,
        { schema: paymentReconciliationSchema },
      ),
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
    mutationFn: (payload: Partial<OrgBilling> & SensitiveAuthPayload) =>
      api<OrgBilling>(apiPaths.billing(orgId || ""), {
        method: "PUT",
        body: JSON.stringify({
          billing_email: payload.billing_email,
          invoice_enabled: payload.invoice_enabled,
          plan_label: payload.plan_label,
          billing_notes: payload.billing_notes,
        }),
        headers: payload.reauthToken ? { "X-Reauth-Token": payload.reauthToken } : undefined,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.billing(orgId || "") }),
  });
}

export function useBillingCheckout() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useMutation({
    mutationFn: (payload: { price_id: string; success_url: string; cancel_url: string } & SensitiveAuthPayload) =>
      api<BillingCheckoutResult>(apiPaths.billingCheckout(orgId || ""), {
        method: "POST",
        body: JSON.stringify({
          price_id: payload.price_id,
          success_url: payload.success_url,
          cancel_url: payload.cancel_url,
        }),
        headers: payload.reauthToken ? { "X-Reauth-Token": payload.reauthToken } : undefined,
        schema: billingUrlSchema,
      }),
  });
}

export function useBillingPortal() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useMutation({
    mutationFn: (payload: { return_url: string } & SensitiveAuthPayload) =>
      api<BillingPortalResult>(apiPaths.billingPortal(orgId || ""), {
        method: "POST",
        body: JSON.stringify({ return_url: payload.return_url }),
        headers: payload.reauthToken ? { "X-Reauth-Token": payload.reauthToken } : undefined,
        schema: billingUrlSchema,
      }),
  });
}

export function useAuthReauth() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useMutation({
    mutationFn: (payload: { password: string; mfa_code?: string; mfa_recovery_code?: string }) =>
      api<{ ok: boolean; token: string; token_type: string; expires_in: number }>(`${apiPaths.reauth}?org_id=${orgId}`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  });
}

export function useMfaStatus() {
  return useQuery({
    queryKey: ["mfaStatus"],
    queryFn: () => api<MfaStatus>(apiPaths.mfaStatus),
  });
}

export function useMfaSetup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { password: string }) =>
      api<{ secret: string; otpauth_url: string }>(apiPaths.mfaSetup, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mfaStatus"] }),
  });
}

export function useMfaEnable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { code: string }) =>
      api<{ recovery_codes: string[] }>(apiPaths.mfaEnable, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mfaStatus"] }),
  });
}

export function useMfaDisable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { password: string; code: string }) =>
      api<{ ok: boolean }>(apiPaths.mfaDisable, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mfaStatus"] }),
  });
}

export function useMfaRegenerateRecoveryCodes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { password: string; code: string }) =>
      api<{ recovery_codes: string[] }>(apiPaths.mfaRecoveryRegenerate, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mfaStatus"] }),
  });
}

export function useAuthSessions() {
  return useQuery({
    queryKey: ["authSessions"],
    queryFn: async () => {
      const mode = process.env.NEXT_PUBLIC_AUTH_MODE || "bearer";
      const refresh = mode === "cookie" ? null : getRefreshToken();
      const query = refresh ? `?refresh_token=${encodeURIComponent(refresh)}` : "";
      const out = await api<{ items: AuthSession[] }>(`${apiPaths.authSessions}${query}`);
      return out.items;
    },
  });
}

export function useRevokeSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api<{ ok: boolean }>(apiPaths.authRevokeSession(id), {
        method: "DELETE",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["authSessions"] }),
  });
}

export function useRevokeOtherSessions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => {
      const mode = process.env.NEXT_PUBLIC_AUTH_MODE || "bearer";
      const refresh = mode === "cookie" ? null : getRefreshToken();
      return api<{ ok: boolean; revoked: number }>(apiPaths.authRevokeOthers, {
        method: "POST",
        body: JSON.stringify({ refresh_token: refresh || undefined }),
      });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["authSessions"] }),
  });
}

export function useRequestAccountDeletion() {
  return useMutation({
    mutationFn: (payload: { reason?: string }) =>
      api<DeletionRequestResult>(apiPaths.authDeleteAccount, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  });
}

export function useRequestOrgDeletion() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useMutation({
    mutationFn: (payload: { reason?: string } & SensitiveAuthPayload) =>
      api<DeletionRequestResult>(apiPaths.deleteOrg(orgId || ""), {
        method: "POST",
        body: JSON.stringify({ reason: payload.reason }),
        headers: payload.reauthToken ? { "X-Reauth-Token": payload.reauthToken } : undefined,
      }),
  });
}

export function useMyDeletionRequests() {
  return useQuery({
    queryKey: ["myDeletionRequests"],
    queryFn: () => api<DeletionRequestList>(apiPaths.authDeleteAccountRequests, { schema: deletionRequestListSchema }),
  });
}

export function useOrgDeletionRequests() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  return useQuery({
    queryKey: ["orgDeletionRequests", orgId || ""],
    queryFn: () =>
      api<DeletionRequestList>(`${apiPaths.adminDeletionRequests}?org_id=${orgId}`, {
        schema: deletionRequestListSchema,
      }),
    enabled: Boolean(orgId && role === "OWNER"),
  });
}
