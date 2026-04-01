"use client";

import Link from "next/link";

import { BellRing } from "lucide-react";

import { AIInsightPanel } from "@/components/common/ai-insight-panel";
import { AlertCard } from "@/components/common/alert-card";
import { EmptyState } from "@/components/common/empty-state";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { Button } from "@/components/ui/button";
import { formatMoney } from "@/lib/utils/format";
import type { Alert } from "@/types/domain";

type BudgetThresholdAlert = {
  alertId: string;
  category: string;
  actualAmount: number;
  plannedAmount: number;
  variancePct: number;
  periodMonth?: string | null;
};

type AiSummary = {
  headline: string;
  highlights: string[];
  risks: string[];
  actions: string[];
  confidence: string;
};

export function PriorityAlertsPanel({
  loading,
  alerts,
  maxImpact,
  onOpenAlert,
  budgetThresholdAlerts,
  budgetThresholdPct,
  aiSummary,
  aiFallbackUsed,
}: {
  loading: boolean;
  alerts: Alert[];
  maxImpact: number;
  onOpenAlert: (alertId: string) => void;
  budgetThresholdAlerts: BudgetThresholdAlert[];
  budgetThresholdPct: number | null;
  aiSummary: AiSummary | null;
  aiFallbackUsed?: boolean | null;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
      <Panel>
        <PanelHeader className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Priority alerts</h2>
          <Button asChild variant="ghost">
            <Link href="/app/alerts">View all</Link>
          </Button>
        </PanelHeader>
        <PanelBody className="space-y-3">
          {budgetThresholdAlerts.length > 0 ? (
            <div data-testid="budget-threshold-alerts" className="rounded-2xl border border-warning/35 bg-warning/10 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-warning">
                <BellRing className="h-4 w-4" />
                Budget threshold alerts ({budgetThresholdAlerts.length})
              </div>
              <div className="mt-2 space-y-1 text-sm">
                {budgetThresholdAlerts.map((item) => (
                  <p key={item.alertId}>
                    {item.category}: {formatMoney(item.actualAmount)} actual vs {formatMoney(item.plannedAmount)} planned
                    {" "}({item.variancePct.toFixed(1)}% over)
                    {item.periodMonth ? ` in ${item.periodMonth}` : ""}
                  </p>
                ))}
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                {budgetThresholdPct !== null
                  ? `Configured threshold: ${budgetThresholdPct.toFixed(1)}% variance over planned.`
                  : "Threshold configured in Organization Settings."}
              </p>
            </div>
          ) : null}
          {!loading && alerts.length === 0 && budgetThresholdAlerts.length === 0 ? (
            <EmptyState eyebrow="All clear" title="No open alerts." description="Current monitoring did not detect active anomalies or leak signals." />
          ) : null}
          {alerts.map((alert) => (
            <button key={alert.id} type="button" className="block w-full text-left" onClick={() => onOpenAlert(alert.id)}>
              <AlertCard alert={alert} maxImpact={maxImpact} />
            </button>
          ))}
        </PanelBody>
      </Panel>

      <AIInsightPanel summary={aiSummary} fallbackUsed={aiFallbackUsed ?? undefined} />
    </div>
  );
}
