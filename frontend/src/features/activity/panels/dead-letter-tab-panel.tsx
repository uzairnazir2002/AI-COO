"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatDate } from "@/lib/utils/format";

type DeadLetterItem = {
  id: string;
  source_type: string;
  source_name: string;
  attempts: number;
  last_failed_at: string;
  status: string;
  last_error: string | null;
  payload: Record<string, unknown>;
};

type RuntimeMetricsView = {
  worker_health?: string;
  queue_lag_seconds?: number;
  dead_letter_open?: number;
  db_active_connections?: number;
  auth_lockout_escalations_total?: number;
};

export function DeadLetterTabPanel({
  isOwner,
  runtimeMetrics,
  deadLetterStatus,
  setDeadLetterStatus,
  deadLetterCounts,
  deadLetterItems,
  deadLetterTotal,
  deadLetterPage,
  deadLetterPageSize,
  onPrevDeadLetterPage,
  onNextDeadLetterPage,
  dismissDeadLetterPending,
  replayDeadLetterPending,
  onDismissDeadLetter,
  onReplayDeadLetter,
}: {
  isOwner: boolean;
  runtimeMetrics?: RuntimeMetricsView;
  deadLetterStatus: string;
  setDeadLetterStatus: (value: string) => void;
  deadLetterCounts: Record<string, number>;
  deadLetterItems: DeadLetterItem[];
  deadLetterTotal: number;
  deadLetterPage: number;
  deadLetterPageSize: number;
  onPrevDeadLetterPage: () => void;
  onNextDeadLetterPage: () => void;
  dismissDeadLetterPending: boolean;
  replayDeadLetterPending: boolean;
  onDismissDeadLetter: (eventId: string) => Promise<void>;
  onReplayDeadLetter: (eventId: string) => Promise<void>;
}) {
  if (!isOwner) return null;

  return (
    <section id="activity-dead-letter" className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Operational diagnostics</CardTitle>
          <CardDescription>DLQ replay controls, queue lag, and worker-health indicators in one panel.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-5">
            <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
              <p className="text-xs uppercase text-muted-foreground">Worker health</p>
              <p className={`mt-2 text-sm font-semibold ${runtimeMetrics?.worker_health === "degraded" ? "text-danger" : "text-emerald-600"}`}>
                {runtimeMetrics?.worker_health ?? "-"}
              </p>
            </div>
            <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
              <p className="text-xs uppercase text-muted-foreground">Queue lag</p>
              <p className="mt-2 text-sm font-semibold">{runtimeMetrics?.queue_lag_seconds ?? 0}s</p>
            </div>
            <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
              <p className="text-xs uppercase text-muted-foreground">Dead-letter open</p>
              <p className="mt-2 text-sm font-semibold">{runtimeMetrics?.dead_letter_open ?? 0}</p>
            </div>
            <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
              <p className="text-xs uppercase text-muted-foreground">DB active</p>
              <p className="mt-2 text-sm font-semibold">{runtimeMetrics?.db_active_connections ?? 0}</p>
            </div>
            <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
              <p className="text-xs uppercase text-muted-foreground">Lockout escalations</p>
              <p className="mt-2 text-sm font-semibold">{runtimeMetrics?.auth_lockout_escalations_total ?? 0}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="w-40">
              <Select value={deadLetterStatus} onValueChange={setDeadLetterStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All statuses</SelectItem>
                  <SelectItem value="OPEN">Open</SelectItem>
                  <SelectItem value="REPLAYED">Replayed</SelectItem>
                  <SelectItem value="DISMISSED">Dismissed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {Object.entries(deadLetterCounts).map(([key, value]) => (
              <Badge key={key} variant={key === "OPEN" ? "destructive" : key === "REPLAYED" ? "success" : "secondary"}>
                {key}: {value}
              </Badge>
            ))}
          </div>

          {deadLetterItems.length === 0 ? (
            <p className="text-sm text-muted-foreground">No dead-letter entries for this filter.</p>
          ) : (
            deadLetterItems.map((item) => (
              <div key={item.id} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium">{item.source_type}: {item.source_name}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Attempts {item.attempts} | Last failed {formatDate(item.last_failed_at)}
                    </p>
                  </div>
                  <Badge variant={item.status === "OPEN" ? "destructive" : item.status === "REPLAYED" ? "success" : "secondary"}>
                    {item.status}
                  </Badge>
                </div>
                {item.last_error ? <p className="mt-3 text-xs text-danger">{item.last_error}</p> : null}
                <pre className="mt-3 overflow-auto rounded-[18px] border border-border/60 bg-background/65 p-3 text-xs">
                  {JSON.stringify(item.payload ?? {}, null, 2)}
                </pre>
                {item.status === "OPEN" ? (
                  <div className="mt-3 flex flex-wrap justify-end gap-2">
                    <Button variant="outline" size="sm" disabled={dismissDeadLetterPending} onClick={() => void onDismissDeadLetter(item.id)}>
                      Dismiss
                    </Button>
                    <Button size="sm" disabled={replayDeadLetterPending} onClick={() => void onReplayDeadLetter(item.id)}>
                      Replay
                    </Button>
                  </div>
                ) : null}
              </div>
            ))
          )}

          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">{deadLetterTotal} total dead-letter rows</p>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={deadLetterPage <= 1} onClick={onPrevDeadLetterPage}>
                Prev
              </Button>
              <span className="text-sm">Page {deadLetterPage}</span>
              <Button variant="outline" size="sm" disabled={Boolean(deadLetterPage * deadLetterPageSize >= deadLetterTotal)} onClick={onNextDeadLetterPage}>
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

