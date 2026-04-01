"use client";

import { DetailDrawer } from "@/components/drawers/detail-drawer";

export function CalculationDrawer({
  open,
  onClose,
  metricLabel,
  formula,
  inputs,
}: {
  open: boolean;
  onClose: () => void;
  metricLabel: string;
  formula: string;
  inputs: Array<{ label: string; value: string; source?: string }>;
}) {
  return (
    <DetailDrawer open={open} onClose={onClose} title={`${metricLabel} calculation`}>
      <div className="space-y-4">
        <div className="rounded-xl border border-border/70 bg-card/70 p-3">
          <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Formula</p>
          <p className="mt-2 text-sm font-medium">{formula}</p>
        </div>
        <div className="space-y-2">
          {inputs.map((input) => (
            <div key={input.label} className="rounded-xl border border-border/70 bg-card/70 px-3 py-2 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">{input.label}</span>
                <span className="font-medium">{input.value}</span>
              </div>
              {input.source ? <p className="mt-1 text-[11px] text-muted-foreground">Source: {input.source}</p> : null}
            </div>
          ))}
        </div>
      </div>
    </DetailDrawer>
  );
}
