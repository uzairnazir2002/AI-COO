"use client";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { formatMoney } from "@/lib/utils/format";

export function SensitivityPanel({
  revenueLiftPct,
  expenseDeltaPct,
  projectedNet,
}: {
  revenueLiftPct: number;
  expenseDeltaPct: number;
  projectedNet: number;
}) {
  return (
    <Panel data-testid="forecast-sensitivity-panel">
      <PanelHeader>
        <h2 className="text-base font-semibold">Runway sensitivity</h2>
      </PanelHeader>
      <PanelBody className="grid gap-2 text-sm md:grid-cols-3">
        <div className="rounded-xl border border-border/70 bg-card/70 p-3">
          <p className="text-xs text-muted-foreground">Revenue lift</p>
          <p className="mt-1 font-semibold">{revenueLiftPct.toFixed(1)}%</p>
        </div>
        <div className="rounded-xl border border-border/70 bg-card/70 p-3">
          <p className="text-xs text-muted-foreground">Expense delta</p>
          <p className="mt-1 font-semibold">{expenseDeltaPct.toFixed(1)}%</p>
        </div>
        <div className="rounded-xl border border-border/70 bg-card/70 p-3">
          <p className="text-xs text-muted-foreground">Projected net impact</p>
          <p className="mt-1 font-semibold">{formatMoney(projectedNet)}</p>
        </div>
      </PanelBody>
    </Panel>
  );
}
