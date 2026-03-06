"use client";

import { useState } from "react";

import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useBillingCheckout, useBillingPortal, useInviteMember, useOrgBilling, useOrgMembers, useOrgSettings, usePlanUsage, useUpdateOrgBilling, useUpdateOrgSettings } from "@/features/settings/hooks";
import { canEdit, isOwner } from "@/lib/auth/rbac";
import { useAppStore } from "@/store/appStore";
import type { Role } from "@/types/domain";

const roleDescriptions: Record<Role, string> = {
  OWNER: "Full access, including invites, org settings, billing, reports, and transactions.",
  EDITOR: "Can manage transactions, settings, and reports but cannot invite members or manage billing ownership.",
  VIEWER: "Read-only access to dashboards, alerts, forecasts, reports, and transaction history.",
};

export default function SettingsPage() {
  const selectedOrg = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId));
  const role = selectedOrg?.role;
  const toast = useToast();

  const members = useOrgMembers();
  const invite = useInviteMember();
  const settings = useOrgSettings();
  const planUsage = usePlanUsage();
  const billing = useOrgBilling();
  const updateSettings = useUpdateOrgSettings();
  const updateBilling = useUpdateOrgBilling();
  const billingCheckout = useBillingCheckout();
  const billingPortal = useBillingPortal();

  const [email, setEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("VIEWER");

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
                    misc_growth_multiplier: String(fd.get("misc_growth_multiplier")),
                    anomaly_spike_multiplier: String(fd.get("anomaly_spike_multiplier")),
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
              <Input name="misc_growth_multiplier" defaultValue={settings.data.misc_growth_multiplier} disabled={!canEdit(role)} />
              <Input name="anomaly_spike_multiplier" defaultValue={settings.data.anomaly_spike_multiplier} disabled={!canEdit(role)} />
              {canEdit(role) ? <Button type="submit">Save</Button> : <p className="text-sm text-muted-foreground">Read-only for viewers.</p>}
            </form>
          ) : (
            <p className="text-sm text-muted-foreground">Starting cash not configurable in MVP for this org.</p>
          )}
        </CardContent>
      </Card>

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
                        const result = await billingPortal.mutateAsync({ return_url: `${window.location.origin}/app/settings` });
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
        <CardHeader><CardTitle>Members</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {!isOwner(role) ? <p className="text-sm text-muted-foreground">Only owners can view and invite members.</p> : null}

          {isOwner(role) ? (
            <form
              className="flex flex-wrap gap-2"
              onSubmit={async (e) => {
                e.preventDefault();
                const result = await invite.mutateAsync({ email, role: inviteRole });
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
    </div>
  );
}
