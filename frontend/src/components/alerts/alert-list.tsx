"use client";

import type { Alert } from "@/types/domain";

export function AlertList({
  alerts,
  onOpenAlert,
  onDismiss,
}: {
  alerts: Alert[];
  onOpenAlert: (id: string) => void;
  onDismiss?: (id: string) => Promise<void>;
}) {
  return (
    <div className="space-y-2">
      {alerts.map((alert) => (
        <div key={alert.id} className="rounded-xl border border-border/70 bg-card/70 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold">{alert.title}</p>
            <span className="rounded-full border border-border/70 px-2 py-0.5 text-[11px] uppercase text-muted-foreground">{alert.severity}</span>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">{alert.description}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-lg border border-border/70 px-2.5 py-1 text-xs hover:bg-muted"
              onClick={() => onOpenAlert(alert.id)}
            >
              Review
            </button>
            {onDismiss ? (
              <button
                type="button"
                className="rounded-lg border border-border/70 px-2.5 py-1 text-xs hover:bg-muted"
                onClick={() => void onDismiss(alert.id)}
              >
                Dismiss
              </button>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}

