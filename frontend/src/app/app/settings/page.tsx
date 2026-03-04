"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/components/common/use-toast";
import { useInviteMember, useOrgMembers, useOrgSettings, useUpdateOrgSettings } from "@/features/settings/hooks";
import { isOwner } from "@/lib/auth/rbac";
import { useAppStore } from "@/store/appStore";
import type { Role } from "@/types/domain";

export default function SettingsPage() {
  const selectedOrg = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId));
  const role = selectedOrg?.role;
  const toast = useToast();

  const members = useOrgMembers();
  const invite = useInviteMember();
  const settings = useOrgSettings();
  const updateSettings = useUpdateOrgSettings();

  const [email, setEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("VIEWER");

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <Card>
        <CardHeader><CardTitle>Organization</CardTitle></CardHeader>
        <CardContent>
          <p className="font-medium">{selectedOrg?.name ?? "No org selected"}</p>
          <p className="text-sm text-muted-foreground">Role: {selectedOrg?.role ?? "-"}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Financial settings</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {settings.data ? (
            <form
              className="grid gap-2 md:grid-cols-3"
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
              <Input name="starting_cash" defaultValue={settings.data.starting_cash} disabled={!isOwner(role)} />
              <Input name="runway_alert_threshold_days" type="number" defaultValue={settings.data.runway_alert_threshold_days} disabled={!isOwner(role)} />
              <Input
                name="vendor_concentration_threshold_pct"
                defaultValue={settings.data.vendor_concentration_threshold_pct}
                disabled={!isOwner(role)}
              />
              <Input name="misc_growth_multiplier" defaultValue={settings.data.misc_growth_multiplier} disabled={!isOwner(role)} />
              <Input name="anomaly_spike_multiplier" defaultValue={settings.data.anomaly_spike_multiplier} disabled={!isOwner(role)} />
              {isOwner(role) ? <Button type="submit">Save</Button> : <p className="text-sm text-muted-foreground">Read-only for non-owners.</p>}
            </form>
          ) : (
            <p className="text-sm text-muted-foreground">Starting cash not configurable in MVP for this org.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Members</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {!isOwner(role) ? <p className="text-sm text-muted-foreground">Only Owners can view/invite members.</p> : null}

          {isOwner(role) ? (
            <form
              className="flex flex-wrap gap-2"
              onSubmit={async (e) => {
                e.preventDefault();
                const result = await invite.mutateAsync({ email, role: inviteRole });
                toast.toast({
                  title: "Invite created",
                  description: result.invite_token ? `Token: ${result.invite_token}` : "Invite sent",
                });
                setEmail("");
              }}
            >
              <Input type="email" placeholder="member@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required className="max-w-xs" />
              <div className="w-32">
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
              <div key={member.user_id} className="flex items-center justify-between rounded-md border p-3">
                <p>{member.email}</p>
                <Badge>{member.role}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
