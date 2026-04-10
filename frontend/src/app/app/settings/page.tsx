"use client";

import { useEffect, useRef, useState } from "react";

import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { TabNav } from "@/components/layout/tab-nav";
import { InlineErrorBanner } from "@/components/states/inline-error-banner";
import { RetryCard } from "@/components/states/retry-card";
import { SkeletonPanel } from "@/components/states/skeleton-panel";
import { SuccessStateCard } from "@/components/states/success-state-card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import {
  useAuthReauth,
  useAuthSessions,
  useBillingCheckout,
  useBillingPortal,
  useBankConnections,
  useDeleteBankConnection,
  useMfaDisable,
  useMfaEnable,
  useMfaRegenerateRecoveryCodes,
  useMfaSetup,
  useMfaStatus,
  useMyDeletionRequests,
  useOrgBilling,
  useOrgDeletionRequests,
  useOrgMembers,
  useOrgSettings,
  usePaymentConnections,
  usePaymentReconciliation,
  usePlanUsage,
  usePlaidExchange,
  usePlaidLinkToken,
  useRevokeOtherSessions,
  useRevokeSession,
  useStripeConnect,
  useSyncBankConnection,
  useUpdateOrgBilling,
  useUpdateOrgSettings,
} from "@/features/settings/hooks";
import {
  useCreateLocation,
  useDeactivateLocation,
  useLocations,
  useUpdateLocation,
} from "@/features/locations/hooks";
import { BillingPanel } from "@/features/settings/panels/billing-panel";
import { CompliancePanel } from "@/features/settings/panels/compliance-panel";
import { DangerPanel } from "@/features/settings/panels/danger-panel";
import { GeneralPanel } from "@/features/settings/panels/general-panel";
import { IntegrationsPanel } from "@/features/settings/panels/integrations-panel";
import { SecurityPanel } from "@/features/settings/panels/security-panel";
import { TeamPanel } from "@/features/settings/panels/team-panel";
import { useSettingsServiceAdapter } from "@/features/settings/services/use-settings-service-adapter";
import { useAppStore } from "@/store/appStore";
import type { PlaidLinkHandler } from "@/types/plaid-link";
import type { Role } from "@/types/domain";

const roleDescriptions: Record<Role, string> = {
  OWNER: "Full access, including invites, org settings, billing, reports, and transactions.",
  EDITOR: "Can manage transactions, settings, and reports but cannot invite members or manage billing ownership.",
  VIEWER: "Read-only access to dashboards, alerts, forecasts, reports, and transaction history.",
};

const plaidScriptUrl = process.env.NEXT_PUBLIC_PLAID_LINK_SCRIPT_URL || "https://cdn.plaid.com/link/v2/stable/link-initialize.js";
let plaidScriptPromise: Promise<void> | null = null;

const MFA_ACTION_PASSWORD_MIN = 8;

function ensurePlaidScript(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Plaid Link is only available in the browser."));
  }
  if (window.Plaid) return Promise.resolve();
  if (plaidScriptPromise) return plaidScriptPromise;

  plaidScriptPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>("script[data-plaid-link='1']");
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Failed to load Plaid Link script.")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = plaidScriptUrl;
    script.async = true;
    script.defer = true;
    script.dataset.plaidLink = "1";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Plaid Link script."));
    document.head.appendChild(script);
  });

  return plaidScriptPromise;
}

export default function SettingsPage() {
  const selectedOrg = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId));
  const experienceTier = useAppStore((s) => s.experienceTier);
  const role = selectedOrg?.role;
  const toast = useToast();
  const settingsServices = useSettingsServiceAdapter();

  const members = useOrgMembers();
  const settings = useOrgSettings();
  const locations = useLocations({ includeInactive: true });
  const createLocation = useCreateLocation();
  const updateLocation = useUpdateLocation();
  const deactivateLocation = useDeactivateLocation();
  const planUsage = usePlanUsage();
  const billing = useOrgBilling();
  const bankConnections = useBankConnections();
  const paymentConnections = usePaymentConnections();
  const stripeConnect = useStripeConnect();
  const plaidLinkToken = usePlaidLinkToken();
  const plaidExchange = usePlaidExchange();
  const syncBankConnection = useSyncBankConnection();
  const deleteBankConnection = useDeleteBankConnection();
  const updateSettings = useUpdateOrgSettings();
  const updateBilling = useUpdateOrgBilling();
  const billingCheckout = useBillingCheckout();
  const billingPortal = useBillingPortal();
  const mfaStatus = useMfaStatus();
  const mfaSetup = useMfaSetup();
  const mfaEnable = useMfaEnable();
  const mfaDisable = useMfaDisable();
  const mfaRegenerateRecoveryCodes = useMfaRegenerateRecoveryCodes();
  const sessions = useAuthSessions();
  const revokeSession = useRevokeSession();
  const revokeOtherSessions = useRevokeOtherSessions();
  const authReauth = useAuthReauth();
  const myDeletionRequests = useMyDeletionRequests();
  const orgDeletionRequests = useOrgDeletionRequests();

  const [email, setEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("VIEWER");
  const [mfaPassword, setMfaPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [setupSecret, setSetupSecret] = useState("");
  const [setupUri, setSetupUri] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [accountDeleteReason, setAccountDeleteReason] = useState("");
  const [orgDeleteReason, setOrgDeleteReason] = useState("");
  const [confirmPhrase, setConfirmPhrase] = useState("");
  const [reauthPassword, setReauthPassword] = useState("");
  const [reauthMfaCode, setReauthMfaCode] = useState("");
  const [reauthToken, setReauthToken] = useState<string | null>(null);
  const [reauthExpiresAt, setReauthExpiresAt] = useState<string | null>(null);
  const [plaidPublicToken, setPlaidPublicToken] = useState("");
  const [plaidInstitutionName, setPlaidInstitutionName] = useState("");
  const [lastLinkToken, setLastLinkToken] = useState<string | null>(null);
  const [isPlaidOpening, setIsPlaidOpening] = useState(false);
  const [plaidDegradedMessage, setPlaidDegradedMessage] = useState<string | null>(null);
  const [bankAction, setBankAction] = useState<{ type: "sync" | "revoke"; id: string } | null>(null);
  const [stripeProviderAccountId, setStripeProviderAccountId] = useState("");
  const [stripeAccountLabel, setStripeAccountLabel] = useState("");
  const [locationName, setLocationName] = useState("");
  const [locationCode, setLocationCode] = useState("");
  const [activeTab, setActiveTab] = useState("general");
  const [showAdvancedTabs, setShowAdvancedTabs] = useState(experienceTier === "advanced");
  const [reconFrom, setReconFrom] = useState(() => new Date(Date.now() - 29 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
  const [reconTo, setReconTo] = useState(() => new Date().toISOString().slice(0, 10));
  const paymentReconciliation = usePaymentReconciliation({ dateFrom: reconFrom, dateTo: reconTo });
  const plaidHandlerRef = useRef<PlaidLinkHandler | null>(null);
  const bankConnectionsError = bankConnections.error instanceof Error ? bankConnections.error.message : null;
  const paymentConnectionsError = paymentConnections.error instanceof Error ? paymentConnections.error.message : null;
  const paymentReconciliationErrorStatus = paymentReconciliation.error instanceof ApiError ? paymentReconciliation.error.status : null;
  const paymentReconciliationError = paymentReconciliation.error instanceof Error ? paymentReconciliation.error.message : null;
  const billingDegradedMessage =
    billing.error instanceof ApiError
      ? (() => {
          const msg = billing.error.message || "";
          const normalized = msg.toLowerCase();
          if (billing.error.status === 409 && normalized.includes("not configured")) {
            return "Stripe billing is not configured on this backend. You can still view usage, but checkout/portal actions will be unavailable until Stripe keys are set.";
          }
          if (billing.error.status === 401) {
            return "Your session is not authorized to load billing. Sign in again and retry.";
          }
          if (billing.error.status === 403) {
            return "You do not have permission to access billing for this organization.";
          }
          if (billing.error.status >= 500) {
            return "Billing is temporarily unavailable due to a backend error. Retry in a moment or check server logs.";
          }
          return null;
        })()
      : null;

  useEffect(() => {
    if (experienceTier === "advanced") setShowAdvancedTabs(true);
  }, [experienceTier]);

  useEffect(() => {
    if (showAdvancedTabs) return;
    if (activeTab === "compliance" || activeTab === "danger") {
      setActiveTab("general");
    }
  }, [activeTab, showAdvancedTabs]);

  useEffect(() => {
    setPlaidDegradedMessage(null);
  }, [selectedOrg?.org_id]);

  function handleReauthRequired(err: unknown): boolean {
    const message = err instanceof Error ? err.message : String(err || "");
    if (!message) return false;
    if (message.toLowerCase().includes("re-authentication is required")) {
      setActiveTab("security");
      toast.toast({
        title: "Re-authentication required",
        description: "Go to Security → Sensitive action re-auth, authorize, then retry the action.",
        variant: "danger",
      });
      return true;
    }
    return false;
  }

  function maybeSetPlaidDegraded(err: unknown) {
    const message = err instanceof Error ? err.message : String(err || "");
    if (!message) return;
    const normalized = message.toLowerCase();
    if (normalized.includes("plaid") && normalized.includes("not configured")) {
      setPlaidDegradedMessage(
        "Backend Plaid credentials are not configured. Connections and syncing are unavailable until keys are set.",
      );
      return;
    }
    if (normalized.includes("plaid api error")) {
      setPlaidDegradedMessage(
        "Plaid returned an API error. Verify Plaid environment, products, and webhook configuration on the backend.",
      );
    }
  }
  const tabLoading =
    activeTab === "general"
      ? settings.isLoading || locations.isLoading
      : activeTab === "team"
        ? members.isLoading
        : activeTab === "security"
          ? settings.isLoading || mfaStatus.isLoading || sessions.isLoading
          : activeTab === "integrations"
            ? bankConnections.isLoading || paymentConnections.isLoading || paymentReconciliation.isLoading
            : activeTab === "billing"
              ? planUsage.isLoading || billing.isLoading
              : activeTab === "compliance"
                ? myDeletionRequests.isLoading || orgDeletionRequests.isLoading
                : false;
  const tabError =
    activeTab === "general"
      ? (settings.error as Error | undefined)?.message || (locations.error as Error | undefined)?.message
      : activeTab === "team"
        ? (members.error as Error | undefined)?.message
        : activeTab === "security"
          ? (settings.error as Error | undefined)?.message || (mfaStatus.error as Error | undefined)?.message || (sessions.error as Error | undefined)?.message
          : activeTab === "integrations"
            ? bankConnectionsError || paymentConnectionsError || paymentReconciliationError
            : activeTab === "billing"
              ? (planUsage.error as Error | undefined)?.message || (billing.error as Error | undefined)?.message
              : activeTab === "compliance"
                ? (myDeletionRequests.error as Error | undefined)?.message || (orgDeletionRequests.error as Error | undefined)?.message
                : null;

  useEffect(() => {
    return () => {
      try {
        plaidHandlerRef.current?.destroy();
      } catch {
        // noop
      }
      plaidHandlerRef.current = null;
    };
  }, []);

  async function openPlaidLink() {
    try {
      setIsPlaidOpening(true);
      const out = await plaidLinkToken.mutateAsync();
      setLastLinkToken(out.link_token);
      await ensurePlaidScript();
      if (!window.Plaid?.create) {
        throw new Error("Plaid Link is unavailable. Verify script loading and CSP settings.");
      }
      try {
        plaidHandlerRef.current?.destroy();
      } catch {
        // noop
      }
      plaidHandlerRef.current = window.Plaid.create({
        token: out.link_token,
        onSuccess: async (publicToken, metadata) => {
          try {
            await plaidExchange.mutateAsync({
              publicToken,
              institutionName: metadata.institution?.name || undefined,
            });
            setPlaidDegradedMessage(null);
            toast.toast({ title: "Bank connection added", variant: "success" });
          } catch (err) {
            maybeSetPlaidDegraded(err);
            toast.toast({ title: err instanceof Error ? err.message : "Bank connection failed", variant: "danger" });
          } finally {
            setIsPlaidOpening(false);
          }
        },
        onExit: (error) => {
          if (error?.display_message || error?.error_message) {
            toast.toast({
              title: error.display_message || error.error_message || "Plaid Link exited",
              variant: "danger",
            });
          }
          setIsPlaidOpening(false);
        },
      });
      plaidHandlerRef.current.open();
    } catch (err) {
      setIsPlaidOpening(false);
      maybeSetPlaidDegraded(err);
      toast.toast({ title: err instanceof Error ? err.message : "Failed to open Plaid Link", variant: "danger" });
    }
  }

  return (
    <div className="space-y-4">
      <SectionHeader
        title="Settings"
        description="Organization controls, usage visibility, member invitations, and clear RBAC behavior."
        actions={(
          <Button variant="outline" size="sm" onClick={() => setShowAdvancedTabs((value) => !value)}>
            {showAdvancedTabs ? "Hide advanced tabs" : "Show advanced tabs"}
          </Button>
        )}
      />

      <TabNav
        active={activeTab}
        onChange={setActiveTab}
        items={[
          { id: "general", label: "Business" },
          { id: "team", label: "Team" },
          { id: "security", label: "Security" },
          { id: "integrations", label: "Integrations" },
          { id: "billing", label: "Billing" },
          ...(showAdvancedTabs ? [{ id: "compliance", label: "Compliance" }, { id: "danger", label: "Danger Zone" }] : []),
        ]}
      />

      {tabLoading ? <SkeletonPanel rows={4} /> : null}

      {tabError ? (
        <div className="space-y-3">
          <InlineErrorBanner message={tabError} />
          <RetryCard
            message="Retry loading this settings tab."
            onRetry={() => {
              if (activeTab === "general") {
                void settings.refetch();
                void locations.refetch();
                return;
              }
              if (activeTab === "team") {
                void members.refetch();
                return;
              }
              if (activeTab === "security") {
                void settings.refetch();
                void mfaStatus.refetch();
                void sessions.refetch();
                return;
              }
              if (activeTab === "integrations") {
                void bankConnections.refetch();
                void paymentConnections.refetch();
                void paymentReconciliation.refetch();
                return;
              }
              if (activeTab === "billing") {
                void planUsage.refetch();
                void billing.refetch();
                return;
              }
              if (activeTab === "compliance") {
                void myDeletionRequests.refetch();
                void orgDeletionRequests.refetch();
              }
            }}
          />
        </div>
      ) : null}

      {reauthToken ? (
        <SuccessStateCard
          title="Sensitive action authorization active"
          description={`Token expires at ${reauthExpiresAt ?? "soon"}.`}
        />
      ) : null}

      {activeTab === "general" ? (
        <GeneralPanel
          role={role}
          selectedOrgName={selectedOrg?.name}
          roleDescriptions={roleDescriptions}
          settingsData={settings.data}
          onSaveSettings={async (formData) => {
            try {
              await updateSettings.mutateAsync({
                starting_cash: String(formData.get("starting_cash")),
                runway_alert_threshold_days: Number(formData.get("runway_alert_threshold_days")),
                vendor_concentration_threshold_pct: String(formData.get("vendor_concentration_threshold_pct")),
                budget_variance_alert_threshold_pct: String(formData.get("budget_variance_alert_threshold_pct")),
                misc_growth_multiplier: String(formData.get("misc_growth_multiplier")),
                anomaly_spike_multiplier: String(formData.get("anomaly_spike_multiplier")),
                reauthToken: reauthToken || undefined,
              });
              toast.toast({ title: "Settings updated" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "Update failed", variant: "danger" });
            }
          }}
          locationName={locationName}
          setLocationName={setLocationName}
          locationCode={locationCode}
          setLocationCode={setLocationCode}
          onCreateLocation={async () => {
            try {
              await createLocation.mutateAsync({
                name: locationName,
                code: locationCode || null,
                is_active: true,
              });
              setLocationName("");
              setLocationCode("");
              toast.toast({ title: "Location created", variant: "success" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "Failed to create location", variant: "danger" });
            }
          }}
          createLocationPending={createLocation.isPending}
          locations={locations.data || []}
          onArchiveLocation={async (id) => {
            try {
              await deactivateLocation.mutateAsync(id);
              toast.toast({ title: "Location archived", variant: "success" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "Failed to archive location", variant: "danger" });
            }
          }}
          onActivateLocation={async (id) => {
            try {
              await updateLocation.mutateAsync({ id, is_active: true });
              toast.toast({ title: "Location reactivated", variant: "success" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "Failed to update location", variant: "danger" });
            }
          }}
        />
      ) : null}

      {activeTab === "security" ? (
        <SecurityPanel
          role={role}
          settingsData={settings.data}
          onSaveOwnerPolicy={async (formData) => {
            try {
              await updateSettings.mutateAsync({
                owner_mfa_required: String(formData.get("owner_mfa_required")) === "on",
                owner_session_max_minutes: Number(formData.get("owner_session_max_minutes")),
                sensitive_action_reauth_minutes: Number(formData.get("sensitive_action_reauth_minutes")),
                reauthToken: reauthToken || undefined,
              });
              toast.toast({ title: "Owner policy updated", variant: "success" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "Policy update failed", variant: "danger" });
            }
          }}
          reauthPassword={reauthPassword}
          setReauthPassword={setReauthPassword}
          reauthMfaCode={reauthMfaCode}
          setReauthMfaCode={setReauthMfaCode}
          reauthToken={reauthToken}
          reauthExpiresAt={reauthExpiresAt}
          onAuthorize={async () => {
            try {
              const out = await authReauth.mutateAsync({
                password: reauthPassword,
                mfa_code: reauthMfaCode || undefined,
              });
              setReauthToken(out.token);
              setReauthExpiresAt(new Date(Date.now() + out.expires_in * 1000).toISOString());
              toast.toast({ title: "Sensitive action authorization active", variant: "success" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "Re-auth failed", variant: "danger" });
            }
          }}
          onClearReauth={() => {
            setReauthToken(null);
            setReauthExpiresAt(null);
          }}
          mfaEnabled={Boolean(mfaStatus.data?.enabled)}
          recoveryCodesRemaining={mfaStatus.data?.recovery_codes_remaining}
          mfaPassword={mfaPassword}
          setMfaPassword={setMfaPassword}
          mfaCode={mfaCode}
          setMfaCode={setMfaCode}
          setupSecret={setupSecret}
          setupUri={setupUri}
          recoveryCodes={recoveryCodes}
          onGenerateMfaSecret={async () => {
            if (mfaPassword.length < MFA_ACTION_PASSWORD_MIN) {
              toast.toast({
                title: `Password must be at least ${MFA_ACTION_PASSWORD_MIN} characters.`,
                variant: "danger",
              });
              return;
            }
            try {
              const result = await mfaSetup.mutateAsync({ password: mfaPassword });
              setSetupSecret(result.secret);
              setSetupUri(result.otpauth_url);
              toast.toast({ title: "MFA secret generated" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "MFA setup failed", variant: "danger" });
            }
          }}
          onEnableMfa={async () => {
            try {
              const result = await mfaEnable.mutateAsync({ code: mfaCode });
              setRecoveryCodes(result.recovery_codes || []);
              setMfaCode("");
              setSetupSecret("");
              setSetupUri("");
              toast.toast({ title: "MFA enabled" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "MFA enable failed", variant: "danger" });
            }
          }}
          onDisableMfa={async () => {
            if (mfaPassword.length < MFA_ACTION_PASSWORD_MIN) {
              toast.toast({
                title: `Password must be at least ${MFA_ACTION_PASSWORD_MIN} characters.`,
                variant: "danger",
              });
              return;
            }
            try {
              await mfaDisable.mutateAsync({ password: mfaPassword, code: mfaCode });
              setMfaCode("");
              toast.toast({ title: "MFA disabled", variant: "warning" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "MFA disable failed", variant: "danger" });
            }
          }}
          onRegenerateRecoveryCodes={async () => {
            if (mfaPassword.length < MFA_ACTION_PASSWORD_MIN) {
              toast.toast({
                title: `Password must be at least ${MFA_ACTION_PASSWORD_MIN} characters.`,
                variant: "danger",
              });
              return;
            }
            try {
              const result = await mfaRegenerateRecoveryCodes.mutateAsync({ password: mfaPassword, code: mfaCode });
              setRecoveryCodes(result.recovery_codes || []);
              toast.toast({ title: "Recovery codes regenerated" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "Regeneration failed", variant: "danger" });
            }
          }}
          sessions={sessions.data ?? []}
          onRevokeOtherSessions={async () => {
            try {
              const result = await revokeOtherSessions.mutateAsync();
              toast.toast({ title: `Revoked ${result.revoked} sessions` });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "Failed to revoke sessions", variant: "danger" });
            }
          }}
          onRevokeSession={async (sessionId) => {
            try {
              await revokeSession.mutateAsync(sessionId);
              toast.toast({ title: "Session revoked" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "Revoke failed", variant: "danger" });
            }
          }}
        />
      ) : null}

      {activeTab === "billing" ? (
        <BillingPanel
          role={role}
          planUsageData={planUsage.data}
          billingData={billing.data}
          billingDegradedMessage={billingDegradedMessage}
          onSaveBilling={async (formData) => {
            try {
              await updateBilling.mutateAsync({
                billing_email: String(formData.get("billing_email") || ""),
                plan_label: String(formData.get("plan_label") || "FREE"),
                billing_notes: String(formData.get("billing_notes") || ""),
                invoice_enabled: String(formData.get("invoice_enabled")) === "on",
                reauthToken: reauthToken || undefined,
              });
              toast.toast({ title: "Billing settings updated" });
            } catch (err) {
              if (handleReauthRequired(err)) return;
              toast.toast({ title: err instanceof Error ? err.message : "Billing update failed", variant: "danger" });
            }
          }}
          onStartCheckout={async () => {
            if (!billing.data) return;
            try {
              const result = await billingCheckout.mutateAsync({
                price_id: billing.data.plan_label,
                success_url: `${window.location.origin}/app/settings?billing=success`,
                cancel_url: `${window.location.origin}/app/settings?billing=cancelled`,
                reauthToken: reauthToken || undefined,
              });
              window.location.href = result.url;
            } catch (err) {
              if (handleReauthRequired(err)) return;
              toast.toast({ title: err instanceof Error ? err.message : "Checkout failed", variant: "danger" });
            }
          }}
          onOpenPortal={async () => {
            try {
              const result = await billingPortal.mutateAsync({
                return_url: `${window.location.origin}/app/settings`,
                reauthToken: reauthToken || undefined,
              });
              window.location.href = result.url;
            } catch (err) {
              if (handleReauthRequired(err)) return;
              toast.toast({ title: err instanceof Error ? err.message : "Portal failed", variant: "danger" });
            }
          }}
        />
      ) : null}

      {activeTab === "integrations" ? (
        <IntegrationsPanel
          role={role}
          plaidDegradedMessage={plaidDegradedMessage}
          isPlaidOpening={isPlaidOpening}
          plaidLinkTokenPending={plaidLinkToken.isPending}
          plaidExchangePending={plaidExchange.isPending}
          onOpenPlaidLink={openPlaidLink}
          lastLinkToken={lastLinkToken}
          plaidPublicToken={plaidPublicToken}
          setPlaidPublicToken={setPlaidPublicToken}
          plaidInstitutionName={plaidInstitutionName}
          setPlaidInstitutionName={setPlaidInstitutionName}
          onManualPlaidExchange={async () => {
            try {
              await plaidExchange.mutateAsync({
                publicToken: plaidPublicToken.trim(),
                institutionName: plaidInstitutionName.trim() || undefined,
              });
              setPlaidPublicToken("");
              setPlaidInstitutionName("");
              setPlaidDegradedMessage(null);
              toast.toast({ title: "Bank connection added", variant: "success" });
            } catch (err) {
              maybeSetPlaidDegraded(err);
              toast.toast({ title: err instanceof Error ? err.message : "Bank connection failed", variant: "danger" });
            }
          }}
          bankConnectionsLoading={bankConnections.isLoading}
          bankConnectionsError={bankConnectionsError}
          bankConnections={bankConnections.data ?? []}
          syncBankConnectionPending={syncBankConnection.isPending}
          deleteBankConnectionPending={deleteBankConnection.isPending}
          bankAction={bankAction}
          onSyncConnection={async (id) => {
            setBankAction({ type: "sync", id });
            try {
              const out = await syncBankConnection.mutateAsync(id);
              toast.toast({ title: `Sync enqueued (${out.status})`, description: out.job_id, variant: "success" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "Sync enqueue failed", variant: "danger" });
            } finally {
              setBankAction((current) => (current?.type === "sync" && current.id === id ? null : current));
            }
          }}
          onRevokeConnection={async (id) => {
            setBankAction({ type: "revoke", id });
            try {
              await deleteBankConnection.mutateAsync(id);
              toast.toast({ title: "Connection revoked", variant: "warning" });
            } catch (err) {
              toast.toast({ title: err instanceof Error ? err.message : "Revoke failed", variant: "danger" });
            } finally {
              setBankAction((current) => (current?.type === "revoke" && current.id === id ? null : current));
            }
          }}
          stripeProviderAccountId={stripeProviderAccountId}
          setStripeProviderAccountId={setStripeProviderAccountId}
          stripeAccountLabel={stripeAccountLabel}
          setStripeAccountLabel={setStripeAccountLabel}
          stripeConnectPending={stripeConnect.isPending}
          onConnectStripe={async () => {
            try {
              const out = await stripeConnect.mutateAsync({
                providerAccountId: stripeProviderAccountId.trim() || undefined,
                accountLabel: stripeAccountLabel.trim() || undefined,
              });
              toast.toast({
                title: "Stripe connection saved",
                description: out.connection.provider_account_id || "Platform account",
                variant: "success",
              });
            } catch (err) {
              if (handleReauthRequired(err)) return;
              if (err instanceof ApiError) {
                if (err.status === 401) {
                  toast.toast({ title: "Session expired. Sign in again and retry.", variant: "danger" });
                  return;
                }
                if (err.status === 403) {
                  toast.toast({ title: "You don’t have permission to connect Stripe for this org.", variant: "danger" });
                  return;
                }
                if (err.status === 0) {
                  toast.toast({ title: "Network request failed. Check API availability and retry.", variant: "danger" });
                  return;
                }
                if (err.status >= 500) {
                  toast.toast({
                    title: "Stripe connection failed due to a backend error.",
                    description: "Retry in a moment or check server logs.",
                    variant: "danger",
                  });
                  return;
                }
              }
              toast.toast({ title: err instanceof Error ? err.message : "Stripe connect failed", variant: "danger" });
            }
          }}
          paymentConnectionsLoading={paymentConnections.isLoading}
          paymentConnectionsError={paymentConnectionsError}
          paymentConnections={paymentConnections.data ?? []}
          reconFrom={reconFrom}
          setReconFrom={setReconFrom}
          reconTo={reconTo}
          setReconTo={setReconTo}
          paymentReconciliationFetching={paymentReconciliation.isFetching}
          paymentReconciliationLoading={paymentReconciliation.isLoading}
          paymentReconciliationErrorStatus={paymentReconciliationErrorStatus}
          paymentReconciliationError={paymentReconciliationError}
          paymentReconciliationData={paymentReconciliation.data}
          onRefreshReconciliation={async () => {
            await paymentReconciliation.refetch();
          }}
        />
      ) : null}

      {activeTab === "team" ? (
        <TeamPanel
          role={role}
          email={email}
          setEmail={setEmail}
          inviteRole={inviteRole}
          setInviteRole={setInviteRole}
          invitePending={settingsServices.invitePending}
          onInvite={async () => {
            try {
              await settingsServices.inviteMember(email, inviteRole, reauthToken || undefined);
              setEmail("");
            } catch (err) {
              if (handleReauthRequired(err)) return;
              toast.toast({ title: err instanceof Error ? err.message : "Invite failed", variant: "danger" });
            }
          }}
          members={members.data ?? []}
          roleDescriptions={roleDescriptions}
        />
      ) : null}

      {activeTab === "compliance" ? (
        <CompliancePanel
          role={role}
          accountDeleteReason={accountDeleteReason}
          setAccountDeleteReason={setAccountDeleteReason}
          requestAccountDeletionPending={settingsServices.requestAccountDeletionPending}
          onRequestAccountDeletion={async () => {
            try {
              await settingsServices.requestAccountDeletionAction(accountDeleteReason || undefined);
              setAccountDeleteReason("");
            } catch (err) {
              if (handleReauthRequired(err)) return;
              toast.toast({ title: err instanceof Error ? err.message : "Account deletion request failed", variant: "danger" });
            }
          }}
          latestAccountDeletion={myDeletionRequests.data?.items[0]}
          orgDeleteReason={orgDeleteReason}
          setOrgDeleteReason={setOrgDeleteReason}
          confirmPhrase={confirmPhrase}
          setConfirmPhrase={setConfirmPhrase}
          requestOrgDeletionPending={settingsServices.requestOrgDeletionPending}
          onRequestOrgDeletion={async () => {
            try {
              await settingsServices.requestOrgDeletionAction(orgDeleteReason || undefined, reauthToken || undefined);
              setOrgDeleteReason("");
              setConfirmPhrase("");
            } catch (err) {
              if (handleReauthRequired(err)) return;
              toast.toast({ title: err instanceof Error ? err.message : "Organization deletion request failed", variant: "danger" });
            }
          }}
          latestOrgDeletion={orgDeletionRequests.data?.items[0]}
        />
      ) : null}

      {activeTab === "danger" ? <DangerPanel /> : null}
    </div>
  );
}
