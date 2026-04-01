"use client";

import { FieldHelpCallout } from "@/components/safety/field-help-callout";
import { FormSection } from "@/components/safety/form-section";
import { RoleAwareDisabledHint } from "@/components/safety/role-aware-disabled-hint";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { isOwner } from "@/lib/auth/rbac";
import type { AuthSession, Role, OrgSettings } from "@/types/domain";

export function SecurityPanel({
  role,
  settingsData,
  onSaveOwnerPolicy,
  reauthPassword,
  setReauthPassword,
  reauthMfaCode,
  setReauthMfaCode,
  reauthToken,
  reauthExpiresAt,
  onAuthorize,
  onClearReauth,
  mfaEnabled,
  recoveryCodesRemaining,
  mfaPassword,
  setMfaPassword,
  mfaCode,
  setMfaCode,
  setupSecret,
  setupUri,
  recoveryCodes,
  onGenerateMfaSecret,
  onEnableMfa,
  onDisableMfa,
  onRegenerateRecoveryCodes,
  sessions,
  onRevokeOtherSessions,
  onRevokeSession,
}: {
  role?: Role;
  settingsData?: OrgSettings;
  onSaveOwnerPolicy: (formData: FormData) => Promise<void>;
  reauthPassword: string;
  setReauthPassword: (value: string) => void;
  reauthMfaCode: string;
  setReauthMfaCode: (value: string) => void;
  reauthToken: string | null;
  reauthExpiresAt: string | null;
  onAuthorize: () => Promise<void>;
  onClearReauth: () => void;
  mfaEnabled: boolean;
  recoveryCodesRemaining?: number;
  mfaPassword: string;
  setMfaPassword: (value: string) => void;
  mfaCode: string;
  setMfaCode: (value: string) => void;
  setupSecret: string;
  setupUri: string;
  recoveryCodes: string[];
  onGenerateMfaSecret: () => Promise<void>;
  onEnableMfa: () => Promise<void>;
  onDisableMfa: () => Promise<void>;
  onRegenerateRecoveryCodes: () => Promise<void>;
  sessions: AuthSession[];
  onRevokeOtherSessions: () => Promise<void>;
  onRevokeSession: (id: string) => Promise<void>;
}) {
  return (
    <section id="settings-security" className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader><CardTitle>Owner security policy</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {!isOwner(role) ? (
              <RoleAwareDisabledHint role={role} requiredRole="OWNER" />
            ) : settingsData ? (
              <FormSection
                title="Policy controls"
                description="These controls enforce owner-level session and re-auth requirements."
              >
                <form
                  className="grid gap-3 md:grid-cols-3"
                  onSubmit={async (event) => {
                    event.preventDefault();
                    await onSaveOwnerPolicy(new FormData(event.currentTarget as HTMLFormElement));
                  }}
                >
                  <label className="flex items-center gap-2 text-sm md:col-span-3">
                    <input name="owner_mfa_required" type="checkbox" defaultChecked={settingsData.owner_mfa_required} />
                    Require MFA for all owners
                  </label>
                  <Input
                    name="owner_session_max_minutes"
                    type="number"
                    min={5}
                    max={1440}
                    defaultValue={settingsData.owner_session_max_minutes}
                    placeholder="Owner session max minutes"
                  />
                  <Input
                    name="sensitive_action_reauth_minutes"
                    type="number"
                    min={5}
                    max={1440}
                    defaultValue={settingsData.sensitive_action_reauth_minutes}
                    placeholder="Sensitive-action re-auth minutes"
                  />
                  <Button type="submit">Save owner policy</Button>
                </form>
              </FormSection>
            ) : (
              <RoleAwareDisabledHint role={role} requiredRole="OWNER" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Sensitive action re-auth</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <FieldHelpCallout
              title="What this does"
              description="Authorize once, then retry blocked sensitive actions such as policy changes or destructive operations."
            />
            <FormSection title="Re-auth credentials">
              <Input
                placeholder="Current password"
                type="password"
                value={reauthPassword}
                onChange={(event) => setReauthPassword(event.target.value)}
              />
              <Input
                placeholder="MFA code (if enabled)"
                value={reauthMfaCode}
                onChange={(event) => setReauthMfaCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                inputMode="numeric"
              />
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => void onAuthorize()}>
                  Authorize
                </Button>
                <Button variant="ghost" onClick={onClearReauth}>
                  Clear
                </Button>
              </div>
              {reauthToken ? (
                <p className="text-xs text-muted-foreground">
                  Active re-auth token{reauthExpiresAt ? ` until ${reauthExpiresAt}` : ""}.
                </p>
              ) : null}
            </FormSection>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader><CardTitle>Multi-factor authentication</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Status: <span className="font-medium text-foreground">{mfaEnabled ? "Enabled" : "Disabled"}</span>
            </p>
            {mfaEnabled ? (
              <p className="text-xs text-muted-foreground">Recovery codes remaining: {recoveryCodesRemaining ?? 0}</p>
            ) : null}
            {!mfaEnabled ? (
              <>
                <Input
                  placeholder="Current password"
                  type="password"
                  value={mfaPassword}
                  onChange={(event) => setMfaPassword(event.target.value)}
                />
                <Button variant="outline" onClick={() => void onGenerateMfaSecret()}>
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
                      onChange={(event) => setMfaCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                      inputMode="numeric"
                    />
                    <Button onClick={() => void onEnableMfa()}>
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
                  onChange={(event) => setMfaPassword(event.target.value)}
                />
                <Input
                  placeholder="Current 6-digit MFA code"
                  value={mfaCode}
                  onChange={(event) => setMfaCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  inputMode="numeric"
                />
                <Button variant="outline" onClick={() => void onDisableMfa()}>
                  Disable MFA
                </Button>
                <Button variant="outline" onClick={() => void onRegenerateRecoveryCodes()}>
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
            <Button variant="outline" onClick={() => void onRevokeOtherSessions()}>
              Revoke other sessions
            </Button>
            <div className="space-y-2">
              {sessions.map((session) => (
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
                        <Button size="sm" variant="outline" onClick={() => void onRevokeSession(session.id)}>
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
    </section>
  );
}
