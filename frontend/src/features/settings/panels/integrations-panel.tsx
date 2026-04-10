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
  plaidDegradedMessage,
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
  paymentReconciliationErrorStatus,
  paymentReconciliationError,
  paymentReconciliationData,
  onRefreshReconciliation,
}: {
  role?: Role;
  plaidDegradedMessage?: string | null;
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
  paymentReconciliationErrorStatus?: number | null;
  paymentReconciliationError: string | null;
  paymentReconciliationData?: PaymentReconciliation;
  onRefreshReconciliation: () => Promise<void>;
}) {
  const plaidDegraded = Boolean(plaidDegradedMessage?.trim());
  const normalizedReconError = (paymentReconciliationError || "").toLowerCase();
  const reconciliationErrorLabel = (() => {
    if (!paymentReconciliationError) return null;
    if (normalizedReconError.includes("date_from must be <=")) {
      return "Invalid date range. Ensure “From” is earlier than “To”, then refresh.";
    }
    if (paymentReconciliationErrorStatus === 401) {
      return "Your session is not authorized to run reconciliation. Sign in again and retry.";
    }
    if (paymentReconciliationErrorStatus === 403) {
      return "You don’t have permission to view reconciliation for this organization.";
    }
    if (paymentReconciliationErrorStatus === 0) {
      return "Network request failed. Verify the API is reachable, then retry.";
    }
    if ((paymentReconciliationErrorStatus || 0) >= 500) {
      return "Reconciliation is temporarily unavailable due to a backend error. Retry in a moment or check server logs.";
    }
    return paymentReconciliationError;
  })();
  const hasStripeConnections = paymentConnections.length > 0;
  const processorCount = paymentReconciliationData?.processor.entry_count ?? null;
  const txCount = paymentReconciliationData?.transactions.entry_count ?? null;
  const showStripeNoIngestionHint = Boolean(paymentReconciliationData) && processorCount === 0 && hasStripeConnections;
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
              {plaidDegraded ? (
                <div className="rounded-[22px] border border-warning/30 bg-warning/5 p-4">
                  <p className="text-sm font-medium">Plaid is unavailable in this environment</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {plaidDegradedMessage}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    If you control the backend, configure <code>PLAID_CLIENT_ID</code> and <code>PLAID_SECRET</code> (and optionally{" "}
                    <code>PLAID_WEBHOOK_URL</code>) then refresh this page.
                  </p>
                </div>
              ) : null}
              <div className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-3">
                <p className="text-sm font-medium">Connect a bank account</p>
                <p className="text-xs text-muted-foreground">
                  Launch Plaid Link to securely connect accounts. On success, the app exchanges the public token automatically.
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="default"
                    disabled={plaidDegraded || isPlaidOpening || plaidLinkTokenPending || plaidExchangePending}
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
                      disabled={plaidDegraded}
                    />
                    <Input
                      placeholder="Institution name (optional)"
                      value={plaidInstitutionName}
                      onChange={(event) => setPlaidInstitutionName(event.target.value)}
                      disabled={plaidDegraded}
                    />
                  </div>
                  <Button
                    className="mt-2"
                    variant="outline"
                    disabled={plaidDegraded || !plaidPublicToken.trim() || plaidExchangePending}
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
              <FieldHelpCallout
                title="How Stripe data arrives"
                description="Reconciliation uses Stripe webhook ingestion. If no webhook events have been processed for this org, processor totals will stay at 0 even if you have a saved connection."
              />
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
              <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                <p className="text-sm font-medium">No Stripe connection configured yet</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Add a mapping above to associate incoming Stripe events with this organization. If webhooks are not configured on the backend, processor totals will remain 0.
                </p>
              </div>
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
            {reconciliationErrorLabel ? (
              <p className="text-sm text-danger">Failed to load reconciliation: {reconciliationErrorLabel}</p>
            ) : null}
            {!hasStripeConnections ? (
              <p className="text-sm text-muted-foreground">
                Reconciliation is available, but processor totals will likely be empty until you configure a Stripe mapping and webhook ingestion starts.
              </p>
            ) : null}
            {showStripeNoIngestionHint ? (
              <div className="rounded-[18px] border border-warning/30 bg-warning/5 p-3">
                <p className="text-sm font-medium">No Stripe processor events detected in this range</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  This usually means Stripe webhooks haven’t been delivered/processed yet for this org, or the selected date range has no events.
                  {txCount === 0 ? " Transactions also show 0 entries in this range." : null}
                </p>
              </div>
            ) : null}
            {paymentReconciliationData ? (
              <div className="grid gap-2 md:grid-cols-3 text-sm">
                <div className="rounded border border-border/60 bg-background/60 px-3 py-2">
                  <p className="text-xs text-muted-foreground">Processor Net</p>
                  <p className="font-medium">{paymentReconciliationData.processor.net}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">{paymentReconciliationData.processor.entry_count} event(s)</p>
                </div>
                <div className="rounded border border-border/60 bg-background/60 px-3 py-2">
                  <p className="text-xs text-muted-foreground">Transactions Net</p>
                  <p className="font-medium">{paymentReconciliationData.transactions.net}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">{paymentReconciliationData.transactions.entry_count} transaction(s)</p>
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
