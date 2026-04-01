"use client";

import type { Alert } from "@/types/domain";

function formatMetaValue(value: unknown) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") return Number.isFinite(value) ? value.toLocaleString() : String(value);
  return String(value);
}

export function AlertDetailPanel({ alert }: { alert: Alert }) {
  const entries = Object.entries(alert.meta || {});
  const metricEntries = entries.filter(([key]) => /(impact|variance|runway|burn|revenue|expense|cash|delta|pct|ratio)/i.test(key));
  const transactionEntries = entries.filter(([key]) => /(transaction|vendor|category|amount|date|reference|import)/i.test(key));

  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-border/70 bg-card/75 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Signal summary</p>
        <h3 className="mt-2 text-xl font-semibold">{alert.title}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{alert.description}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
          <span className="rounded-full border border-border/70 px-2 py-1">Severity: {alert.severity}</span>
          <span className="rounded-full border border-border/70 px-2 py-1">Kind: {alert.kind}</span>
          <span className="rounded-full border border-border/70 px-2 py-1">Status: {alert.status}</span>
        </div>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/75 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Related metrics</p>
        <div className="mt-3 grid gap-2">
          {metricEntries.length === 0 ? (
            <p className="text-xs text-muted-foreground">No metric-specific metadata was provided for this alert.</p>
          ) : (
            metricEntries.map(([key, value]) => (
              <div key={key} className="flex items-center justify-between rounded-xl border border-border/60 bg-background/60 px-3 py-2 text-xs">
                <span className="uppercase tracking-[0.12em] text-muted-foreground">{key.replace(/_/g, " ")}</span>
                <span className="font-medium">{formatMetaValue(value)}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/75 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Related transactions</p>
        <div className="mt-3 grid gap-2">
          {transactionEntries.length === 0 ? (
            <p className="text-xs text-muted-foreground">No transaction-linked metadata is attached to this alert.</p>
          ) : (
            transactionEntries.map(([key, value]) => (
              <div key={key} className="flex items-center justify-between rounded-xl border border-border/60 bg-background/60 px-3 py-2 text-xs">
                <span className="uppercase tracking-[0.12em] text-muted-foreground">{key.replace(/_/g, " ")}</span>
                <span className="font-medium">{formatMetaValue(value)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
