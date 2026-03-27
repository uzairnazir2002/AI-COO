"use client";

import { useEffect, useRef, useState } from "react";

import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  useAuthReauth,
  useAuthSessions,
  useBillingCheckout,
  useBillingPortal,
  useBankConnections,
  useDeleteBankConnection,
  useInviteMember,
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
  useRequestAccountDeletion,
  useRequestOrgDeletion,
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
import { canEdit, isOwner } from "@/lib/auth/rbac";
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
  const role = selectedOrg?.role;
  const toast = useToast();

  const members = useOrgMembers();
  const invite = useInviteMember();
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
  const requestAccountDeletion = useRequestAccountDeletion();
  const requestOrgDeletion = useRequestOrgDeletion();
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
  const [bankAction, setBankAction] = useState<{ type: "sync" | "revoke"; id: string } | null>(null);
  const [stripeProviderAccountId, setStripeProviderAccountId] = useState("");
  const [stripeAccountLabel, setStripeAccountLabel] = useState("");
  const [locationName, setLocationName] = useState("");
  const [locationCode, setLocationCode] = useState("");
  const [reconFrom, setReconFrom] = useState(() => new Date(Date.now() - 29 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
  const [reconTo, setReconTo] = useState(() => new Date().toISOString().slice(0, 10));
  const paymentReconciliation = usePaymentReconciliation({ dateFrom: reconFrom, dateTo: reconTo });
  const plaidHandlerRef = useRef<PlaidLinkHandler | null>(null);
  const bankConnectionsError = bankConnections.error instanceof Error ? bankConnections.error.message : null;
  const paymentConnectionsError = paymentConnections.error instanceof Error ? paymentConnections.error.message : null;
  const paymentReconciliationError = paymentReconciliation.error instanceof Error ? paymentReconciliation.error.message : null;

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
            toast.toast({ title: "Bank connection added", variant: "success" });
          } catch (err) {
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
      toast.toast({ title: err instanceof Error ? err.message : "Failed to open Plaid Link", variant: "danger" });
    }
  }

  return (
    <div className="space-y-4">
      <SectionHeader
        title="Settings"
        description="Organization controls, usage visibility, member invitations, and clear RBAC behavior."
      />

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader><CardTitle>Organization overview</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
              <p className="text-sm text-muted-foreground">Organization</p>
              <p className="mt-1 text-xl font-semibold">{selectedOrg?.name ?? "No org selected"}</p>
            </div>
            <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
              <p className="text-sm text-muted-foreground">Your role</p>
              <div className="mt-2 flex items-center gap-3">
                <Badge>{selectedOrg?.role ?? "-"}</Badge>
                <p className="text-sm text-muted-foreground">{role ? roleDescriptions[role] : "Select an organization to see effective permissions."}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Role guide</CardTitle></CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-3">
            {(Object.keys(roleDescriptions) as Role[]).map((item) => (
              <div key={item} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                <Badge variant={item === "OWNER" ? "default" : item === "EDITOR" ? "warning" : "secondary"}>{item}</Badge>
                <p className="mt-3 text-sm text-muted-foreground">{roleDescriptions[item]}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Financial settings</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {settings.data ? (
            <form
              className="grid gap-3 md:grid-cols-3"
              onSubmit={async (e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget as HTMLFormElement);
                try {
                  await updateSettings.mutateAsync({
                    starting_cash: String(fd.get("starting_cash")),
                    runway_alert_threshold_days: Number(fd.get("runway_alert_threshold_days")),
                    vendor_concentration_threshold_pct: String(fd.get("vendor_concentration_threshold_pct")),
                    budget_variance_alert_threshold_pct: String(fd.get("budget_variance_alert_threshold_pct")),
                    misc_growth_multiplier: String(fd.get("misc_growth_multiplier")),
                    anomaly_spike_multiplier: String(fd.get("anomaly_spike_multiplier")),
                    reauthToken: reauthToken || undefined,
                  });
                  toast.toast({ title: "Settings updated" });
                } catch (err) {
                  toast.toast({ title: err instanceof Error ? err.message : "Update failed", variant: "danger" });
                }
              }}
            >
              <Input name="starting_cash" defaultValue={settings.data.starting_cash} disabled={!canEdit(role)} />
              <Input name="runway_alert_threshold_days" type="number" defaultValue={settings.data.runway_alert_threshold_days} disabled={!canEdit(role)} />
              <Input name="vendor_concentration_threshold_pct" defaultValue={settings.data.vendor_concentration_threshold_pct} disabled={!canEdit(role)} />
              <Input
                name="budget_variance_alert_threshold_pct"
                defaultValue={settings.data.budget_variance_alert_threshold_pct}
                disabled={!canEdit(role)}
              />
              <Input name="misc_growth_multiplier" defaultValue={settings.data.misc_growth_multiplier} disabled={!canEdit(role)} />
              <Input name="anomaly_spike_multiplier" defaultValue={settings.data.anomaly_spike_multiplier} disabled={!canEdit(role)} />
              {canEdit(role) ? <Button type="submit">Save</Button> : <p className="text-sm text-muted-foreground">Read-only for viewers.</p>}
            </form>
          ) : (
            <p className="text-sm text-muted-foreground">Starting cash not configurable in MVP for this org.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Locations</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Manage organization locations used to scope transactions, analytics, runway, and reports.
          </p>
          {canEdit(role) ? (
            <form
              className="grid gap-2 md:grid-cols-[1fr_180px_auto]"
              onSubmit={async (e) => {
                e.preventDefault();
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
            >
              <Input
                placeholder="Location name"
                value={locationName}
                onChange={(e) => setLocationName(e.target.value)}
                required
              />
              <Input
                placeholder="Code (optional)"
                value={locationCode}
                onChange={(e) => setLocationCode(e.target.value)}
              />
              <Button type="submit" disabled={createLocation.isPending || locationName.trim().length === 0}>
                Add location
              </Button>
            </form>
          ) : null}
          {(locations.data || []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No locations configured yet.</p>
          ) : (
            <div className="space-y-2">
              {(locations.data || []).map((location) => (
                <div key={location.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-border/70 bg-card/70 p-3">
                  <div>
                    <p className="font-medium">
                      {location.name}
                      {location.code ? ` (${location.code})` : ""}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {location.is_active ? "Active" : "Inactive"}
                    </p>
                  </div>
                  {canEdit(role) ? (
                    <div className="flex gap-2">
                      {location.is_active ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            try {
                              await deactivateLocation.mutateAsync(location.id);
                              toast.toast({ title: "Location archived", variant: "success" });
                            } catch (err) {
                              toast.toast({
                                title: err instanceof Error ? err.message : "Failed to archive location",
                                variant: "danger",
                              });
                            }
                          }}
                        >
                          Archive
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            try {
                              await updateLocation.mutateAsync({
                                id: location.id,
                                is_active: true,
                              });
                              toast.toast({ title: "Location reactivated", variant: "success" });
                            } catch (err) {
                              toast.toast({
                                title: err instanceof Error ? err.message : "Failed to update location",
                                variant: "danger",
                              });
                            }
                          }}
                        >
                          Activate
                        </Button>
                      )}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader><CardTitle>Owner security policy</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {!isOwner(role) ? (
              <p className="text-sm text-muted-foreground">Only owners can update organization security policy.</p>
            ) : settings.data ? (
              <form
                className="grid gap-3 md:grid-cols-3"
                onSubmit={async (e) => {
                  e.preventDefault();
                  const fd = new FormData(e.currentTarget as HTMLFormElement);
                  try {
                    await updateSettings.mutateAsync({
                      owner_mfa_required: String(fd.get("owner_mfa_required")) === "on",
                      owner_session_max_minutes: Number(fd.get("owner_session_max_minutes")),
                      sensitive_action_reauth_minutes: Number(fd.get("sensitive_action_reauth_minutes")),
                      reauthToken: reauthToken || undefined,
                    });
                    toast.toast({ title: "Owner policy updated", variant: "success" });
                  } catch (err) {
                    toast.toast({ title: err instanceof Error ? err.message : "Policy update failed", variant: "danger" });
                  }
                }}
              >
                <label className="flex items-center gap-2 text-sm md:col-span-3">
                  <input name="owner_mfa_required" type="checkbox" defaultChecked={settings.data.owner_mfa_required} />
                  Require MFA for all owners
                </label>
                <Input
                  name="owner_session_max_minutes"
                  type="number"
                  min={5}
                  max={1440}
                  defaultValue={settings.data.owner_session_max_minutes}
                  placeholder="Owner session max minutes"
                />
                <Input
                  name="sensitive_action_reauth_minutes"
                  type="number"
                  min={5}
                  max={1440}
                  defaultValue={settings.data.sensitive_action_reauth_minutes}
                  placeholder="Sensitive-action re-auth minutes"
                />
                <Button type="submit">Save owner policy</Button>
              </form>
            ) : (
              <p className="text-sm text-muted-foreground">Security policy unavailable for this organization.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Sensitive action re-auth</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              If a sensitive action is blocked by policy, authorize once here and retry.
            </p>
            <Input
              placeholder="Current password"
              type="password"
              value={reauthPassword}
              onChange={(e) => setReauthPassword(e.target.value)}
            />
            <Input
              placeholder="MFA code (if enabled)"
              value={reauthMfaCode}
              onChange={(e) => setReauthMfaCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              inputMode="numeric"
            />
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={async () => {
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
              >
                Authorize
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setReauthToken(null);
                  setReauthExpiresAt(null);
                }}
              >
                Clear
              </Button>
            </div>
            {reauthToken ? (
              <p className="text-xs text-muted-foreground">
                Active re-auth token{reauthExpiresAt ? ` until ${reauthExpiresAt}` : ""}.
              </p>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader><CardTitle>Multi-factor authentication</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Status: <span className="font-medium text-foreground">{mfaStatus.data?.enabled ? "Enabled" : "Disabled"}</span>
            </p>
            {mfaStatus.data?.enabled ? (
              <p className="text-xs text-muted-foreground">Recovery codes remaining: {mfaStatus.data.recovery_codes_remaining}</p>
            ) : null}
            {!mfaStatus.data?.enabled ? (
              <>
                <Input
                  placeholder="Current password"
                  type="password"
                  value={mfaPassword}
                  onChange={(e) => setMfaPassword(e.target.value)}
                />
                <Button
                  variant="outline"
                  onClick={async () => {
                    try {
                      const result = await mfaSetup.mutateAsync({ password: mfaPassword });
                      setSetupSecret(result.secret);
                      setSetupUri(result.otpauth_url);
                      toast.toast({ title: "MFA secret generated" });
                    } catch (err) {
                      toast.toast({ title: err instanceof Error ? err.message : "MFA setup failed", variant: "danger" });
                    }
                  }}
                >
                  Generate MFA secret
                </Button>
                {setupSecret ? (
                  <div className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-2">
                    <p className="text-xs text-muted-foreground">Enter this secret in your authenticator app:</p>
                    <p className="font-mono text-sm break-all">{setupSecret}</p>
                    <p className="text-xs text-muted-foreground break-all">URI: {setupUri}</p>
                    <Input
                      placeholder="6-digit code"
                      value={mfaCode}
                      onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                      inputMode="numeric"
                    />
                    <Button
                      onClick={async () => {
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
                    >
                      Enable MFA
                    </Button>
                  </div>
                ) : null}
              </>
            ) : (
              <>
                <Input
                  placeholder="Current password"
                  type="password"
                  value={mfaPassword}
                  onChange={(e) => setMfaPassword(e.target.value)}
                />
                <Input
                  placeholder="Current 6-digit MFA code"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  inputMode="numeric"
                />
                <Button
                  variant="outline"
                  onClick={async () => {
                    try {
                      await mfaDisable.mutateAsync({ password: mfaPassword, code: mfaCode });
                      setMfaCode("");
                      toast.toast({ title: "MFA disabled", variant: "warning" });
                    } catch (err) {
                      toast.toast({ title: err instanceof Error ? err.message : "MFA disable failed", variant: "danger" });
                    }
                  }}
                >
                  Disable MFA
                </Button>
                <Button
                  variant="outline"
                  onClick={async () => {
                    try {
                      const result = await mfaRegenerateRecoveryCodes.mutateAsync({ password: mfaPassword, code: mfaCode });
                      setRecoveryCodes(result.recovery_codes || []);
                      toast.toast({ title: "Recovery codes regenerated" });
                    } catch (err) {
                      toast.toast({ title: err instanceof Error ? err.message : "Regeneration failed", variant: "danger" });
                    }
                  }}
                >
                  Regenerate recovery codes
                </Button>
              </>
            )}
            {recoveryCodes.length > 0 ? (
              <div className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-2">
                <p className="text-xs text-muted-foreground">Store these recovery codes securely. Each code can be used once.</p>
                <div className="grid gap-1 md:grid-cols-2">
                  {recoveryCodes.map((code) => (
                    <code key={code} className="rounded bg-muted px-2 py-1 text-xs">{code}</code>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Session management</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Button
              variant="outline"
              onClick={async () => {
                try {
                  const result = await revokeOtherSessions.mutateAsync();
                  toast.toast({ title: `Revoked ${result.revoked} sessions` });
                } catch (err) {
                  toast.toast({ title: err instanceof Error ? err.message : "Failed to revoke sessions", variant: "danger" });
                }
              }}
            >
              Revoke other sessions
            </Button>
            <div className="space-y-2">
              {(sessions.data ?? []).map((session) => (
                <div key={session.id} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium">{session.user_agent || "Unknown device"}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        IP {session.ip_address || "-"} | Last used {session.last_used_at || session.created_at}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {session.is_current ? <Badge>Current</Badge> : null}
                      {!session.is_current ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            try {
                              await revokeSession.mutateAsync(session.id);
                              toast.toast({ title: "Session revoked" });
                            } catch (err) {
                              toast.toast({ title: err instanceof Error ? err.message : "Revoke failed", variant: "danger" });
                            }
                          }}
                        >
                          Revoke
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader><CardTitle>Plan & usage</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {!planUsage.data ? (
              <p className="text-sm text-muted-foreground">Usage data unavailable.</p>
            ) : (
              <>
                <p className="text-sm text-muted-foreground">Plan: <span className="font-medium text-foreground">{planUsage.data.plan_code}</span></p>
                <p className="text-xs text-muted-foreground">Billing period start: {planUsage.data.period_start}</p>
                <div className="grid gap-2">
                  {Object.entries(planUsage.data.metrics).map(([metric, value]) => (
                    <div key={metric} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                      <p className="text-xs uppercase text-muted-foreground">{metric.replace(/_/g, " ")}</p>
                      <p className="mt-1 text-lg font-semibold">{value.used} / {value.limit}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Billing (Owner only)</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {!isOwner(role) ? (
              <p className="text-sm text-muted-foreground">Only owners can manage subscriptions and billing settings.</p>
            ) : billing.data ? (
              <div className="space-y-4">
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                    <p className="text-xs uppercase text-muted-foreground">Provider</p>
                    <p className="mt-2 text-sm font-semibold">{billing.data.provider}</p>
                  </div>
                  <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                    <p className="text-xs uppercase text-muted-foreground">Subscription</p>
                    <p className="mt-2 text-sm font-semibold">{billing.data.subscription_status ?? "Not active"}</p>
                  </div>
                  <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                    <p className="text-xs uppercase text-muted-foreground">Current price</p>
                    <p className="mt-2 text-sm font-semibold">{billing.data.active_price_id ?? "None"}</p>
                  </div>
                </div>
                <form
                  className="grid gap-3 md:grid-cols-2"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const fd = new FormData(e.currentTarget as HTMLFormElement);
                    try {
                      await updateBilling.mutateAsync({
                        billing_email: String(fd.get("billing_email") || ""),
                        plan_label: String(fd.get("plan_label") || "FREE"),
                        billing_notes: String(fd.get("billing_notes") || ""),
                        invoice_enabled: String(fd.get("invoice_enabled")) === "on",
                        reauthToken: reauthToken || undefined,
                      });
                      toast.toast({ title: "Billing settings updated" });
                    } catch (err) {
                      toast.toast({ title: err instanceof Error ? err.message : "Billing update failed", variant: "danger" });
                    }
                  }}
                >
                  <Input name="billing_email" defaultValue={billing.data.billing_email || ""} placeholder="billing@example.com" />
                  <Input name="plan_label" defaultValue={billing.data.plan_label} placeholder="FREE / price code" />
                  <Input name="billing_notes" defaultValue={billing.data.billing_notes || ""} placeholder="Billing notes" />
                  <label className="flex items-center gap-2 text-sm">
                    <input name="invoice_enabled" type="checkbox" defaultChecked={billing.data.invoice_enabled} />
                    Invoice workflow enabled
                  </label>
                  <Button type="submit" className="md:col-span-2">Save billing</Button>
                </form>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    onClick={async () => {
                      try {
                        const result = await billingCheckout.mutateAsync({
                          price_id: billing.data.plan_label,
                          success_url: `${window.location.origin}/app/settings?billing=success`,
                          cancel_url: `${window.location.origin}/app/settings?billing=cancelled`,
                          reauthToken: reauthToken || undefined,
                        });
                        window.location.href = result.url;
                      } catch (err) {
                        toast.toast({ title: err instanceof Error ? err.message : "Checkout failed", variant: "danger" });
                      }
                    }}
                  >
                    Start Stripe checkout
                  </Button>
                  <Button
                    variant="outline"
                    onClick={async () => {
                      try {
                        const result = await billingPortal.mutateAsync({
                          return_url: `${window.location.origin}/app/settings`,
                          reauthToken: reauthToken || undefined,
                        });
                        window.location.href = result.url;
                      } catch (err) {
                        toast.toast({ title: err instanceof Error ? err.message : "Portal failed", variant: "danger" });
                      }
                    }}
                  >
                    Open billing portal
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Billing placeholder unavailable.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Bank integrations (Plaid)</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {!canEdit(role) ? (
            <p className="text-sm text-muted-foreground">Only owners and editors can manage bank connections.</p>
          ) : (
            <>
              <div className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-3">
                <p className="text-sm font-medium">Connect a bank account</p>
                <p className="text-xs text-muted-foreground">
                  Launch Plaid Link to securely connect accounts. On success, the app exchanges the public token automatically.
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="default"
                    disabled={isPlaidOpening || plaidLinkToken.isPending || plaidExchange.isPending}
                    onClick={openPlaidLink}
                  >
                    {isPlaidOpening ? "Opening Plaid..." : "Connect with Plaid"}
                  </Button>
                  {lastLinkToken ? (
                    <code className="rounded bg-muted px-2 py-1 text-xs break-all">{lastLinkToken}</code>
                  ) : null}
                </div>
                <details className="rounded border border-border/60 bg-background/60 p-3">
                  <summary className="cursor-pointer text-xs text-muted-foreground">Advanced manual public token exchange</summary>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    <Input
                      placeholder="Plaid public_token"
                      value={plaidPublicToken}
                      onChange={(event) => setPlaidPublicToken(event.target.value)}
                    />
                    <Input
                      placeholder="Institution name (optional)"
                      value={plaidInstitutionName}
                      onChange={(event) => setPlaidInstitutionName(event.target.value)}
                    />
                  </div>
                  <Button
                    className="mt-2"
                    variant="outline"
                    disabled={!plaidPublicToken.trim() || plaidExchange.isPending}
                    onClick={async () => {
                      try {
                        await plaidExchange.mutateAsync({
                          publicToken: plaidPublicToken.trim(),
                          institutionName: plaidInstitutionName.trim() || undefined,
                        });
                        setPlaidPublicToken("");
                        setPlaidInstitutionName("");
                        toast.toast({ title: "Bank connection added", variant: "success" });
                      } catch (err) {
                        toast.toast({ title: err instanceof Error ? err.message : "Bank connection failed", variant: "danger" });
                      }
                    }}
                  >
                    {plaidExchange.isPending ? "Exchanging..." : "Exchange token manually"}
                  </Button>
                </details>
              </div>

              <div className="space-y-2">
                {bankConnections.isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading bank connections...</p>
                ) : null}
                {bankConnectionsError ? (
                  <p className="text-sm text-danger">Failed to load bank connections: {bankConnectionsError}</p>
                ) : null}
                {(bankConnections.data ?? []).map((connection) => (
                  <div key={connection.id} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium">{connection.institution_name || "Unnamed institution"}</p>
                        <p className="text-xs text-muted-foreground">
                          {connection.provider} | {connection.status} | {connection.accounts.length} account(s)
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={
                            syncBankConnection.isPending ||
                            deleteBankConnection.isPending ||
                            connection.status !== "ACTIVE"
                          }
                          onClick={async () => {
                            setBankAction({ type: "sync", id: connection.id });
                            try {
                              const out = await syncBankConnection.mutateAsync(connection.id);
                              toast.toast({ title: `Sync enqueued (${out.status})`, description: out.job_id, variant: "success" });
                            } catch (err) {
                              toast.toast({ title: err instanceof Error ? err.message : "Sync enqueue failed", variant: "danger" });
                            } finally {
                              setBankAction((current) =>
                                current?.type === "sync" && current.id === connection.id ? null : current,
                              );
                            }
                          }}
                        >
                          {syncBankConnection.isPending && bankAction?.type === "sync" && bankAction.id === connection.id
                            ? "Syncing..."
                            : "Sync now"}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={deleteBankConnection.isPending || syncBankConnection.isPending}
                          onClick={async () => {
                            setBankAction({ type: "revoke", id: connection.id });
                            try {
                              await deleteBankConnection.mutateAsync(connection.id);
                              toast.toast({ title: "Connection revoked", variant: "warning" });
                            } catch (err) {
                              toast.toast({ title: err instanceof Error ? err.message : "Revoke failed", variant: "danger" });
                            } finally {
                              setBankAction((current) =>
                                current?.type === "revoke" && current.id === connection.id ? null : current,
                              );
                            }
                          }}
                        >
                          {deleteBankConnection.isPending && bankAction?.type === "revoke" && bankAction.id === connection.id
                            ? "Revoking..."
                            : "Revoke"}
                        </Button>
                      </div>
                    </div>
                    {connection.accounts.length ? (
                      <div className="mt-3 grid gap-2 md:grid-cols-2">
                        {connection.accounts.map((account) => (
                          <div key={account.id} className="rounded border border-border/60 bg-background/60 px-3 py-2">
                            <p className="text-sm font-medium">{account.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {account.account_type || "account"} {account.mask ? `****${account.mask}` : ""}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
                {bankConnections.data && bankConnections.data.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No connected bank accounts yet.</p>
                ) : null}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Payment integrations (Stripe)</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {!canEdit(role) ? (
            <p className="text-sm text-muted-foreground">Only owners and editors can manage payment connections.</p>
          ) : (
            <div className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-3">
              <p className="text-sm font-medium">Connect Stripe account</p>
              <p className="text-xs text-muted-foreground">
                Save Stripe account mapping for this organization. Leave account id blank for direct platform account events.
              </p>
              <div className="grid gap-2 md:grid-cols-2">
                <Input
                  placeholder="Stripe account id (optional, e.g. acct_123)"
                  value={stripeProviderAccountId}
                  onChange={(event) => setStripeProviderAccountId(event.target.value)}
                />
                <Input
                  placeholder="Account label (optional)"
                  value={stripeAccountLabel}
                  onChange={(event) => setStripeAccountLabel(event.target.value)}
                />
              </div>
              <Button
                data-testid="stripe-connect-submit"
                disabled={stripeConnect.isPending}
                onClick={async () => {
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
                    toast.toast({ title: err instanceof Error ? err.message : "Stripe connect failed", variant: "danger" });
                  }
                }}
              >
                {stripeConnect.isPending ? "Saving..." : "Connect / update Stripe"}
              </Button>
            </div>
          )}

          <div className="space-y-2">
            {paymentConnections.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading Stripe connections...</p>
            ) : null}
            {paymentConnectionsError ? (
              <p className="text-sm text-danger">Failed to load Stripe connections: {paymentConnectionsError}</p>
            ) : null}
            {(paymentConnections.data ?? []).map((connection) => (
              <div key={connection.id} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                <p className="text-sm font-medium">{connection.metadata_json.account_label as string || "Stripe connection"}</p>
                <p className="text-xs text-muted-foreground">
                  {connection.provider} | {connection.status} | account {connection.provider_account_id || "platform"}
                </p>
              </div>
            ))}
            {paymentConnections.data && paymentConnections.data.length === 0 ? (
              <p className="text-sm text-muted-foreground">No Stripe connection configured yet.</p>
            ) : null}
          </div>

          <div className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-3" data-testid="stripe-reconciliation-card">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium">Reconciliation (Stripe vs transactions)</p>
              <Button
                variant="outline"
                size="sm"
                disabled={paymentReconciliation.isFetching}
                onClick={() => void paymentReconciliation.refetch()}
              >
                {paymentReconciliation.isFetching ? "Refreshing..." : "Refresh"}
              </Button>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <Input type="date" value={reconFrom} onChange={(event) => setReconFrom(event.target.value)} />
              <Input type="date" value={reconTo} onChange={(event) => setReconTo(event.target.value)} />
            </div>
            {paymentReconciliation.isLoading ? (
              <p className="text-sm text-muted-foreground">Loading reconciliation...</p>
            ) : null}
            {paymentReconciliationError ? (
              <p className="text-sm text-danger">Failed to load reconciliation: {paymentReconciliationError}</p>
            ) : null}
            {paymentReconciliation.data ? (
              <div className="grid gap-2 md:grid-cols-3 text-sm">
                <div className="rounded border border-border/60 bg-background/60 px-3 py-2">
                  <p className="text-xs text-muted-foreground">Processor Net</p>
                  <p className="font-medium">{paymentReconciliation.data.processor.net}</p>
                </div>
                <div className="rounded border border-border/60 bg-background/60 px-3 py-2">
                  <p className="text-xs text-muted-foreground">Transactions Net</p>
                  <p className="font-medium">{paymentReconciliation.data.transactions.net}</p>
                </div>
                <div className="rounded border border-border/60 bg-background/60 px-3 py-2">
                  <p className="text-xs text-muted-foreground">Absolute Delta</p>
                  <p className="font-medium">{paymentReconciliation.data.delta.absolute}</p>
                </div>
              </div>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Members</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {!isOwner(role) ? <p className="text-sm text-muted-foreground">Only owners can view and invite members.</p> : null}

          {isOwner(role) ? (
            <form
              className="flex flex-wrap gap-2"
              onSubmit={async (e) => {
                e.preventDefault();
                const result = await invite.mutateAsync({ email, role: inviteRole, reauthToken: reauthToken || undefined });
                toast.toast({
                  title: "Invite created",
                  description: result.invite_token ? `/auth/register?invite_token=${result.invite_token}` : "Invite sent",
                });
                setEmail("");
              }}
            >
              <Input type="email" placeholder="member@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required className="max-w-xs" />
              <div className="w-40">
                <Select value={inviteRole} onValueChange={(value) => setInviteRole(value as Role)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="VIEWER">Viewer</SelectItem>
                    <SelectItem value="EDITOR">Editor</SelectItem>
                    <SelectItem value="OWNER">Owner</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button disabled={invite.isPending} type="submit">Invite</Button>
            </form>
          ) : null}

          <div className="space-y-2">
            {(members.data ?? []).map((member) => (
              <div key={member.user_id} className="flex items-center justify-between rounded-[22px] border border-border/70 bg-card/70 p-4">
                <div>
                  <p className="font-medium">{member.email}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{roleDescriptions[member.role]}</p>
                </div>
                <Badge>{member.role}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Data & compliance actions</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-3">
            <p className="text-sm font-medium">Account deletion request</p>
            <p className="text-xs text-muted-foreground">
              Creates a scheduled deletion request with a retention window. You can use this for privacy compliance workflows.
            </p>
            <Input
              placeholder="Optional reason for account deletion"
              value={accountDeleteReason}
              onChange={(event) => setAccountDeleteReason(event.target.value)}
            />
            <Button
              variant="outline"
              disabled={requestAccountDeletion.isPending}
              onClick={async () => {
                try {
                  const result = await requestAccountDeletion.mutateAsync({
                    reason: accountDeleteReason || undefined,
                  });
                  toast.toast({
                    title: "Account deletion requested",
                    description: `Request ${result.request_id} queued for ${result.delete_after}.`,
                    variant: "warning",
                  });
                  setAccountDeleteReason("");
                } catch (err) {
                  toast.toast({ title: err instanceof Error ? err.message : "Request failed", variant: "danger" });
                }
              }}
            >
              Request account deletion
            </Button>
            {(myDeletionRequests.data?.items.length ?? 0) > 0 ? (
              <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                <p className="text-xs uppercase text-muted-foreground">Latest account request</p>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant={myDeletionRequests.data?.items[0].status === "PROCESSED" ? "success" : "warning"}>
                    {myDeletionRequests.data?.items[0].status}
                  </Badge>
                  <p className="text-xs text-muted-foreground">
                    delete_after {myDeletionRequests.data?.items[0].delete_after}
                    {myDeletionRequests.data?.items[0].processed_at ? ` | processed_at ${myDeletionRequests.data?.items[0].processed_at}` : ""}
                  </p>
                </div>
              </div>
            ) : null}
          </div>

          <div className="rounded-[22px] border border-danger/30 bg-danger/5 p-4 space-y-3">
            <p className="text-sm font-medium text-danger">Organization deletion request (Owner only)</p>
            <p className="text-xs text-muted-foreground">
              This schedules full organization deletion. Type <code>DELETE</code> to enable the request action.
            </p>
            <Input
              placeholder="Optional reason for organization deletion"
              value={orgDeleteReason}
              onChange={(event) => setOrgDeleteReason(event.target.value)}
              disabled={!isOwner(role)}
            />
            <Input
              placeholder='Type "DELETE" to confirm'
              value={confirmPhrase}
              onChange={(event) => setConfirmPhrase(event.target.value)}
              disabled={!isOwner(role)}
            />
            <Button
              variant="destructive"
              disabled={!isOwner(role) || confirmPhrase !== "DELETE" || requestOrgDeletion.isPending}
              onClick={async () => {
                try {
                  const result = await requestOrgDeletion.mutateAsync({
                    reason: orgDeleteReason || undefined,
                    reauthToken: reauthToken || undefined,
                  });
                  toast.toast({
                    title: "Organization deletion requested",
                    description: `Request ${result.request_id} queued for ${result.delete_after}.`,
                    variant: "warning",
                  });
                  setOrgDeleteReason("");
                  setConfirmPhrase("");
                } catch (err) {
                  toast.toast({ title: err instanceof Error ? err.message : "Request failed", variant: "danger" });
                }
              }}
            >
              Request organization deletion
            </Button>
            {isOwner(role) && (orgDeletionRequests.data?.items.length ?? 0) > 0 ? (
              <div className="rounded-[18px] border border-danger/20 bg-background/65 p-3">
                <p className="text-xs uppercase text-muted-foreground">Latest org deletion request</p>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant={orgDeletionRequests.data?.items[0].status === "PROCESSED" ? "success" : "warning"}>
                    {orgDeletionRequests.data?.items[0].status}
                  </Badge>
                  <p className="text-xs text-muted-foreground">
                    delete_after {orgDeletionRequests.data?.items[0].delete_after}
                    {orgDeletionRequests.data?.items[0].processed_at ? ` | processed_at ${orgDeletionRequests.data?.items[0].processed_at}` : ""}
                  </p>
                </div>
              </div>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
