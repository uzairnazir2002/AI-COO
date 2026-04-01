"use client";

import { FieldHelpCallout } from "@/components/safety/field-help-callout";
import { FormSection } from "@/components/safety/form-section";
import { RoleAwareDisabledHint } from "@/components/safety/role-aware-disabled-hint";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { isOwner } from "@/lib/auth/rbac";
import type { OrgBilling, PlanUsage, Role } from "@/types/domain";

export function BillingPanel({
  role,
  planUsageData,
  billingData,
  onSaveBilling,
  onStartCheckout,
  onOpenPortal,
}: {
  role?: Role;
  planUsageData?: PlanUsage;
  billingData?: OrgBilling;
  onSaveBilling: (formData: FormData) => Promise<void>;
  onStartCheckout: () => Promise<void>;
  onOpenPortal: () => Promise<void>;
}) {
  return (
    <section id="settings-billing" className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader><CardTitle>Plan & usage</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <FormSection
              title="Usage insights"
              description="Track metric limits and plan capacity without changing existing billing contracts."
            >
              {!planUsageData ? (
                <p className="text-sm text-muted-foreground">Usage data unavailable.</p>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground">Plan: <span className="font-medium text-foreground">{planUsageData.plan_code}</span></p>
                  <p className="text-xs text-muted-foreground">Billing period start: {planUsageData.period_start}</p>
                  <div className="grid gap-2">
                    {Object.entries(planUsageData.metrics).map(([metric, value]) => (
                      <div key={metric} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                        <p className="text-xs uppercase text-muted-foreground">{metric.replace(/_/g, " ")}</p>
                        <p className="mt-1 text-lg font-semibold">{value.used} / {value.limit}</p>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </FormSection>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Billing (Owner only)</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {!isOwner(role) ? (
              <RoleAwareDisabledHint role={role} requiredRole="OWNER" />
            ) : billingData ? (
              <FormSection
                title="Owner billing controls"
                description="Manage provider configuration and hosted billing workflows."
              >
                <FieldHelpCallout
                  title="What this does"
                  description="These controls are owner-scoped and preserve current provider checkout and portal flows."
                />
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                    <p className="text-xs uppercase text-muted-foreground">Provider</p>
                    <p className="mt-2 text-sm font-semibold">{billingData.provider}</p>
                  </div>
                  <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                    <p className="text-xs uppercase text-muted-foreground">Subscription</p>
                    <p className="mt-2 text-sm font-semibold">{billingData.subscription_status ?? "Not active"}</p>
                  </div>
                  <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                    <p className="text-xs uppercase text-muted-foreground">Current price</p>
                    <p className="mt-2 text-sm font-semibold">{billingData.active_price_id ?? "None"}</p>
                  </div>
                </div>
                <form
                  className="grid gap-3 md:grid-cols-2"
                  onSubmit={async (event) => {
                    event.preventDefault();
                    await onSaveBilling(new FormData(event.currentTarget as HTMLFormElement));
                  }}
                >
                  <Input name="billing_email" defaultValue={billingData.billing_email || ""} placeholder="billing@example.com" />
                  <Input name="plan_label" defaultValue={billingData.plan_label} placeholder="FREE / price code" />
                  <Input name="billing_notes" defaultValue={billingData.billing_notes || ""} placeholder="Billing notes" />
                  <label className="flex items-center gap-2 text-sm">
                    <input name="invoice_enabled" type="checkbox" defaultChecked={billingData.invoice_enabled} />
                    Invoice workflow enabled
                  </label>
                  <Button type="submit" className="md:col-span-2">Save billing</Button>
                </form>
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" onClick={() => void onStartCheckout()}>
                    Start Stripe checkout
                  </Button>
                  <Button variant="outline" onClick={() => void onOpenPortal()}>
                    Open billing portal
                  </Button>
                </div>
              </FormSection>
            ) : (
              <RoleAwareDisabledHint role={role} requiredRole="OWNER" />
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
