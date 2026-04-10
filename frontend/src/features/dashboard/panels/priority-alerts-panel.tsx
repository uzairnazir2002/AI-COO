"use client";

import Link from "next/link";

import { BellRing } from "lucide-react";

import { AiBriefCard } from "@/components/ai/ai-brief-card";
import { AlertCard } from "@/components/common/alert-card";
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
          <div data-testid="budget-threshold-alerts" className="rounded-2xl border border-warning/35 bg-warning/10 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-warning">
              <BellRing className="h-4 w-4" />
              Budget threshold alerts ({budgetThresholdAlerts.length})
            </div>
            {budgetThresholdAlerts.length > 0 ? (
              <>
                <div className="mt-2 space-y-1 text-sm">
                  {budgetThresholdAlerts.map((item) => (
                    <p key={item.alertId}>
                      {item.category}: {formatMoney(item.actualAmount)} actual vs {formatMoney(item.plannedAmount)} planned{" "}
                      ({item.variancePct.toFixed(1)}% over)
                      {item.periodMonth ? ` in ${item.periodMonth}` : ""}
                    </p>
                  ))}
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  {budgetThresholdPct !== null
                    ? `Configured threshold: ${budgetThresholdPct.toFixed(1)}% variance over planned.`
                    : "Threshold configured in Organization Settings."}
                </p>
              </>
            ) : !loading ? (
              <p className="mt-2 text-sm text-muted-foreground">
                No categories currently exceed your budget threshold for this period. Alerts appear here when variance crosses the
                configured limit.
              </p>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">Loading budget signals…</p>
            )}
          </div>
          {!loading && alerts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No additional operational alerts in this feed.</p>
          ) : null}
          {alerts.map((alert) => (
            <button key={alert.id} type="button" className="block w-full text-left" onClick={() => onOpenAlert(alert.id)}>
              <AlertCard alert={alert} maxImpact={maxImpact} />
            </button>
          ))}
        </PanelBody>
      </Panel>

      <AiBriefCard summary={aiSummary} fallbackUsed={aiFallbackUsed ?? undefined} />
    </div>
  );
}
