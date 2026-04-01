"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { canEdit } from "@/lib/auth/rbac";
import type { Location, OrgSettings, Role } from "@/types/domain";

export function GeneralPanel({
  role,
  selectedOrgName,
  roleDescriptions,
  settingsData,
  onSaveSettings,
  locationName,
  setLocationName,
  locationCode,
  setLocationCode,
  onCreateLocation,
  createLocationPending,
  locations,
  onArchiveLocation,
  onActivateLocation,
}: {
  role?: Role;
  selectedOrgName?: string;
  roleDescriptions: Record<Role, string>;
  settingsData?: OrgSettings;
  onSaveSettings: (formData: FormData) => Promise<void>;
  locationName: string;
  setLocationName: (value: string) => void;
  locationCode: string;
  setLocationCode: (value: string) => void;
  onCreateLocation: () => Promise<void>;
  createLocationPending: boolean;
  locations: Location[];
  onArchiveLocation: (id: string) => Promise<void>;
  onActivateLocation: (id: string) => Promise<void>;
}) {
  return (
    <section id="settings-general" className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader><CardTitle>Organization overview</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
              <p className="text-sm text-muted-foreground">Organization</p>
              <p className="mt-1 text-xl font-semibold">{selectedOrgName ?? "No org selected"}</p>
            </div>
            <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
              <p className="text-sm text-muted-foreground">Your role</p>
              <div className="mt-2 flex items-center gap-3">
                <Badge>{role ?? "-"}</Badge>
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
          {settingsData ? (
            <form
              className="grid gap-3 md:grid-cols-3"
              onSubmit={async (event) => {
                event.preventDefault();
                await onSaveSettings(new FormData(event.currentTarget as HTMLFormElement));
              }}
            >
              <Input name="starting_cash" defaultValue={settingsData.starting_cash} disabled={!canEdit(role)} />
              <Input name="runway_alert_threshold_days" type="number" defaultValue={settingsData.runway_alert_threshold_days} disabled={!canEdit(role)} />
              <Input name="vendor_concentration_threshold_pct" defaultValue={settingsData.vendor_concentration_threshold_pct} disabled={!canEdit(role)} />
              <Input
                name="budget_variance_alert_threshold_pct"
                defaultValue={settingsData.budget_variance_alert_threshold_pct}
                disabled={!canEdit(role)}
              />
              <Input name="misc_growth_multiplier" defaultValue={settingsData.misc_growth_multiplier} disabled={!canEdit(role)} />
              <Input name="anomaly_spike_multiplier" defaultValue={settingsData.anomaly_spike_multiplier} disabled={!canEdit(role)} />
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
              onSubmit={async (event) => {
                event.preventDefault();
                await onCreateLocation();
              }}
            >
              <Input
                placeholder="Location name"
                value={locationName}
                onChange={(event) => setLocationName(event.target.value)}
                required
              />
              <Input
                placeholder="Code (optional)"
                value={locationCode}
                onChange={(event) => setLocationCode(event.target.value)}
              />
              <Button type="submit" disabled={createLocationPending || locationName.trim().length === 0}>
                Add location
              </Button>
            </form>
          ) : null}
          {locations.length === 0 ? (
            <p className="text-sm text-muted-foreground">No locations configured yet.</p>
          ) : (
            <div className="space-y-2">
              {locations.map((location) => (
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
                        <Button size="sm" variant="outline" onClick={() => void onArchiveLocation(location.id)}>
                          Archive
                        </Button>
                      ) : (
                        <Button size="sm" variant="outline" onClick={() => void onActivateLocation(location.id)}>
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
    </section>
  );
}

