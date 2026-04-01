"use client";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { Input } from "@/components/ui/input";
import { formatMoney } from "@/lib/utils/format";

export type ForecastAssumptions = {
  plannedHireCost: string;
  plannedPurchaseCost: string;
  revenueLiftPct: string;
  expenseDeltaPct: string;
};

export function AssumptionsPanel({
  assumptions,
  onChange,
  runwayImpactPreview,
}: {
  assumptions: ForecastAssumptions;
  onChange: (next: ForecastAssumptions) => void;
  runwayImpactPreview: number;
}) {
  return (
    <Panel data-testid="forecast-assumptions-panel">
      <PanelHeader>
        <h2 className="text-base font-semibold">Assumptions lab</h2>
      </PanelHeader>
      <PanelBody className="space-y-3">
        <Input
          placeholder="Planned hire cost (monthly)"
          inputMode="decimal"
          value={assumptions.plannedHireCost}
          onChange={(event) => onChange({ ...assumptions, plannedHireCost: event.target.value })}
        />
        <Input
          placeholder="Planned purchase cost"
          inputMode="decimal"
          value={assumptions.plannedPurchaseCost}
          onChange={(event) => onChange({ ...assumptions, plannedPurchaseCost: event.target.value })}
        />
        <Input
          placeholder="Revenue lift %"
          inputMode="decimal"
          value={assumptions.revenueLiftPct}
          onChange={(event) => onChange({ ...assumptions, revenueLiftPct: event.target.value })}
        />
        <Input
          placeholder="Expense delta %"
          inputMode="decimal"
          value={assumptions.expenseDeltaPct}
          onChange={(event) => onChange({ ...assumptions, expenseDeltaPct: event.target.value })}
        />
        <div className="rounded-xl border border-border/70 bg-card/70 p-3 text-xs text-muted-foreground">
          Runway impact preview: <span className="font-semibold text-foreground">{formatMoney(runwayImpactPreview)}</span>
        </div>
      </PanelBody>
    </Panel>
  );
}
