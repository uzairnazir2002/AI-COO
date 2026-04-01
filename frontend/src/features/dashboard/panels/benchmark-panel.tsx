"use client";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { formatCompactMoney } from "@/lib/utils/format";
import { toNumber } from "@/lib/utils/chart";

type BenchmarkRow = {
  location_id?: string | null;
  location_name: string;
  revenue: string | number | null;
  expense: string | number | null;
  net: string | number | null;
  margin_pct: string | number | null;
};

export function BenchmarkPanel({
  from,
  to,
  rows,
  selectedLocationId,
}: {
  from: string;
  to: string;
  rows: BenchmarkRow[];
  selectedLocationId: string | null;
}) {
  return (
    <Panel>
      <PanelHeader className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Cross-location benchmark</h2>
        <p className="text-xs text-muted-foreground">
          {from} to {to}
        </p>
      </PanelHeader>
      <PanelBody>
        {rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No location-distributed transactions in this range.</p>
        ) : (
          <div className="grid gap-2">
            {rows.slice(0, 6).map((row) => {
              const isActiveScope = selectedLocationId !== null && row.location_id === selectedLocationId;
              return (
                <div
                  key={`${row.location_id ?? "unassigned"}-${row.location_name}`}
                  className={`flex items-center justify-between rounded-xl border px-3 py-2 text-sm ${isActiveScope ? "border-primary/60 bg-primary/5" : "border-border/60"}`}
                >
                  <div>
                    <p className="font-medium">{row.location_name}</p>
                    <p className="text-xs text-muted-foreground">
                      Rev {formatCompactMoney(toNumber(row.revenue))} | Exp {formatCompactMoney(toNumber(row.expense))}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">{formatCompactMoney(toNumber(row.net))}</p>
                    <p className="text-xs text-muted-foreground">
                      Margin {toNumber(row.margin_pct).toFixed(1)}%
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </PanelBody>
    </Panel>
  );
}
