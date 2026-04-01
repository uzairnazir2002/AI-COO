"use client";

import { Badge } from "@/components/ui/badge";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";

export function RiskPanel({
  risk,
  lastPointMonth,
  expenseOverRevenue,
}: {
  risk: boolean;
  lastPointMonth: string | null;
  expenseOverRevenue: number;
}) {
  return (
    <Panel data-testid="forecast-risk-panel">
      <PanelHeader>
        <h2 className="text-base font-semibold">Forecast risks</h2>
      </PanelHeader>
      <PanelBody className="space-y-2 text-sm">
        <div className="flex items-center gap-2">
          <Badge variant={risk ? "warning" : "success"}>{risk ? "Elevated risk" : "Risk stable"}</Badge>
          <span className="text-xs text-muted-foreground">{lastPointMonth ? `Horizon month: ${lastPointMonth}` : "No horizon point"}</span>
        </div>
        <p className="text-xs text-muted-foreground">
          Expense over revenue at horizon: {expenseOverRevenue.toFixed(2)}
        </p>
        <p className="text-xs text-muted-foreground">
          Use scenario and override controls to reduce cashflow pressure before budget lock-in.
        </p>
      </PanelBody>
    </Panel>
  );
}
