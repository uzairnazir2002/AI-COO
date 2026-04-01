"use client";

import { FieldHelpCallout } from "@/components/safety/field-help-callout";
import { FormSection } from "@/components/safety/form-section";
import { RoleAwareDisabledHint } from "@/components/safety/role-aware-disabled-hint";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { canEdit } from "@/lib/auth/rbac";
import type { BankConnection, PaymentConnection, PaymentReconciliation, Role } from "@/types/domain";

type BankAction = { type: "sync" | "revoke"; id: string } | null;

export function IntegrationsPanel({
  role,
  isPlaidOpening,
  plaidLinkTokenPending,
  plaidExchangePending,
  onOpenPlaidLink,
  lastLinkToken,
  plaidPublicToken,
  setPlaidPublicToken,
  plaidInstitutionName,
  setPlaidInstitutionName,
  onManualPlaidExchange,
  bankConnectionsLoading,
  bankConnectionsError,
  bankConnections,
  syncBankConnectionPending,
  deleteBankConnectionPending,
  bankAction,
  onSyncConnection,
  onRevokeConnection,
  stripeProviderAccountId,
  setStripeProviderAccountId,
  stripeAccountLabel,
  setStripeAccountLabel,
  stripeConnectPending,
  onConnectStripe,
  paymentConnectionsLoading,
  paymentConnectionsError,
  paymentConnections,
  reconFrom,
  setReconFrom,
  reconTo,
  setReconTo,
  paymentReconciliationFetching,
  paymentReconciliationLoading,
  paymentReconciliationError,
  paymentReconciliationData,
  onRefreshReconciliation,
}: {
  role?: Role;
  isPlaidOpening: boolean;
  plaidLinkTokenPending: boolean;
  plaidExchangePending: boolean;
  onOpenPlaidLink: () => Promise<void>;
  lastLinkToken: string | null;
  plaidPublicToken: string;
  setPlaidPublicToken: (value: string) => void;
  plaidInstitutionName: string;
  setPlaidInstitutionName: (value: string) => void;
  onManualPlaidExchange: () => Promise<void>;
  bankConnectionsLoading: boolean;
  bankConnectionsError: string | null;
  bankConnections: BankConnection[];
  syncBankConnectionPending: boolean;
  deleteBankConnectionPending: boolean;
  bankAction: BankAction;
  onSyncConnection: (id: string) => Promise<void>;
  onRevokeConnection: (id: string) => Promise<void>;
  stripeProviderAccountId: string;
  setStripeProviderAccountId: (value: string) => void;
  stripeAccountLabel: string;
  setStripeAccountLabel: (value: string) => void;
  stripeConnectPending: boolean;
  onConnectStripe: () => Promise<void>;
  paymentConnectionsLoading: boolean;
  paymentConnectionsError: string | null;
  paymentConnections: PaymentConnection[];
  reconFrom: string;
  setReconFrom: (value: string) => void;
  reconTo: string;
  setReconTo: (value: string) => void;
  paymentReconciliationFetching: boolean;
  paymentReconciliationLoading: boolean;
  paymentReconciliationError: string | null;
  paymentReconciliationData?: PaymentReconciliation;
  onRefreshReconciliation: () => Promise<void>;
}) {
  return (
    <section id="settings-integrations" className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Bank integrations (Plaid)</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {!canEdit(role) ? (
            <RoleAwareDisabledHint role={role} requiredRole="EDITOR" />
          ) : (
            <FormSection
              title="Connect and manage bank accounts"
              description="Launch Plaid Link, sync current institutions, and revoke access when needed."
            >
              <FieldHelpCallout
                title="What this does"
                description="Connected accounts power import and reconciliation workflows. Existing API integration behavior is unchanged."
              />
              <div className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-3">
                <p className="text-sm font-medium">Connect a bank account</p>
                <p className="text-xs text-muted-foreground">
                  Launch Plaid Link to securely connect accounts. On success, the app exchanges the public token automatically.
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="default"
                    disabled={isPlaidOpening || plaidLinkTokenPending || plaidExchangePending}
                    onClick={() => void onOpenPlaidLink()}
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
                    disabled={!plaidPublicToken.trim() || plaidExchangePending}
                    onClick={() => void onManualPlaidExchange()}
                  >
                    {plaidExchangePending ? "Exchanging..." : "Exchange token manually"}
                  </Button>
                </details>
              </div>

              <div className="space-y-2">
                {bankConnectionsLoading ? (
                  <p className="text-sm text-muted-foreground">Loading bank connections...</p>
                ) : null}
                {bankConnectionsError ? (
                  <p className="text-sm text-danger">Failed to load bank connections: {bankConnectionsError}</p>
                ) : null}
                {bankConnections.map((connection) => (
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
                          disabled={syncBankConnectionPending || deleteBankConnectionPending || connection.status !== "ACTIVE"}
                          onClick={() => void onSyncConnection(connection.id)}
                        >
                          {syncBankConnectionPending && bankAction?.type === "sync" && bankAction.id === connection.id
                            ? "Syncing..."
                            : "Sync now"}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={deleteBankConnectionPending || syncBankConnectionPending}
                          onClick={() => void onRevokeConnection(connection.id)}
                        >
                          {deleteBankConnectionPending && bankAction?.type === "revoke" && bankAction.id === connection.id
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
                {bankConnections.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No connected bank accounts yet.</p>
                ) : null}
              </div>
            </FormSection>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Payment integrations (Stripe)</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {!canEdit(role) ? (
            <RoleAwareDisabledHint role={role} requiredRole="EDITOR" />
          ) : (
            <FormSection
              title="Stripe account mapping"
              description="Map processor accounts and validate payments-to-ledger reconciliation."
            >
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
                <Button data-testid="stripe-connect-submit" disabled={stripeConnectPending} onClick={() => void onConnectStripe()}>
                  {stripeConnectPending ? "Saving..." : "Connect / update Stripe"}
                </Button>
              </div>
            </FormSection>
          )}

          <div className="space-y-2">
            {paymentConnectionsLoading ? (
              <p className="text-sm text-muted-foreground">Loading Stripe connections...</p>
            ) : null}
            {paymentConnectionsError ? (
              <p className="text-sm text-danger">Failed to load Stripe connections: {paymentConnectionsError}</p>
            ) : null}
            {paymentConnections.map((connection) => (
              <div key={connection.id} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                <p className="text-sm font-medium">{(connection.metadata_json.account_label as string) || "Stripe connection"}</p>
                <p className="text-xs text-muted-foreground">
                  {connection.provider} | {connection.status} | account {connection.provider_account_id || "platform"}
                </p>
              </div>
            ))}
            {paymentConnections.length === 0 ? (
              <p className="text-sm text-muted-foreground">No Stripe connection configured yet.</p>
            ) : null}
          </div>

          <div className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-3" data-testid="stripe-reconciliation-card">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium">Reconciliation (Stripe vs transactions)</p>
              <Button variant="outline" size="sm" disabled={paymentReconciliationFetching} onClick={() => void onRefreshReconciliation()}>
                {paymentReconciliationFetching ? "Refreshing..." : "Refresh"}
              </Button>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <Input type="date" value={reconFrom} onChange={(event) => setReconFrom(event.target.value)} />
              <Input type="date" value={reconTo} onChange={(event) => setReconTo(event.target.value)} />
            </div>
            {paymentReconciliationLoading ? (
              <p className="text-sm text-muted-foreground">Loading reconciliation...</p>
            ) : null}
            {paymentReconciliationError ? (
              <p className="text-sm text-danger">Failed to load reconciliation: {paymentReconciliationError}</p>
            ) : null}
            {paymentReconciliationData ? (
              <div className="grid gap-2 md:grid-cols-3 text-sm">
                <div className="rounded border border-border/60 bg-background/60 px-3 py-2">
                  <p className="text-xs text-muted-foreground">Processor Net</p>
                  <p className="font-medium">{paymentReconciliationData.processor.net}</p>
                </div>
                <div className="rounded border border-border/60 bg-background/60 px-3 py-2">
                  <p className="text-xs text-muted-foreground">Transactions Net</p>
                  <p className="font-medium">{paymentReconciliationData.transactions.net}</p>
                </div>
                <div className="rounded border border-border/60 bg-background/60 px-3 py-2">
                  <p className="text-xs text-muted-foreground">Absolute Delta</p>
                  <p className="font-medium">{paymentReconciliationData.delta.absolute}</p>
                </div>
              </div>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
