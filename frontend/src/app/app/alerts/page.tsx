"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BellRing } from "lucide-react";

import { AlertCard } from "@/components/common/alert-card";
import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAlerts, useDismissAlert } from "@/features/alerts/hooks";
import { alertImpactValue } from "@/lib/utils/chart";
import type { Alert } from "@/types/domain";

export default function AlertsPage() {
  const [status, setStatus] = useState<"open" | "dismissed">("open");
  const [kind, setKind] = useState("ALL");
  const [activeAlertId, setActiveAlertId] = useState<string | null>(null);
  const alerts = useAlerts(status);
  const dismiss = useDismissAlert();
  const toast = useToast();

  const filtered = useMemo(() => {
    const items = alerts.data?.items ?? [];
    return kind === "ALL" ? items : items.filter((a) => a.kind === kind);
  }, [alerts.data?.items, kind]);
  const maxImpact = useMemo(() => filtered.reduce((acc, row) => Math.max(acc, alertImpactValue(row.meta)), 0), [filtered]);
  const activeAlert = filtered.find((row) => row.id === activeAlertId) ?? null;

  return (
    <div className="space-y-4">
      <SectionHeader
        title="Alerts"
        description="Open and dismissed signals from anomaly detection, runway pressure, and profit leakage monitoring."
        actions={
          <>
            <div className="w-32">
              <Select value={status} onValueChange={(value) => setStatus(value as "open" | "dismissed")}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="dismissed">Dismissed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-44">
              <Select value={kind} onValueChange={setKind}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All kinds</SelectItem>
                  <SelectItem value="ANOMALY">Anomaly</SelectItem>
                  <SelectItem value="PROFIT_LEAK">Profit leak</SelectItem>
                  <SelectItem value="RUNWAY">Runway</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        }
      />

      {filtered.length === 0 ? (
        <EmptyState
          eyebrow="Quiet board"
          title="No alerts in this view."
          description="Signals appear once enough transaction history exists. Use imports or manual entry to activate monitoring."
          actions={[{ label: "Add transactions", href: "/app/transactions" }]}
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BellRing className="h-4 w-4 text-primary" />
              Alert stream
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {filtered.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                maxImpact={maxImpact}
                onOpen={setActiveAlertId}
                onDismiss={
                  status === "open"
                    ? async (id) => {
                        await dismiss.mutateAsync(id);
                        toast.toast({ title: "Alert dismissed" });
                      }
                    : undefined
                }
              />
            ))}
          </CardContent>
        </Card>
      )}

      <AnimatePresence>
        {activeAlert ? (
          <>
            <motion.button
              type="button"
              className="fixed inset-0 z-40 bg-background/55 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setActiveAlertId(null)}
              aria-label="Close alert detail"
            />
            <motion.aside
              initial={{ x: 420 }}
              animate={{ x: 0 }}
              exit={{ x: 420 }}
              className="fixed right-0 top-0 z-50 h-full w-full max-w-xl border-l border-border bg-background p-6 shadow-2xl"
            >
              <AlertDetail alert={activeAlert} onClose={() => setActiveAlertId(null)} />
            </motion.aside>
          </>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function AlertDetail({ alert, onClose }: { alert: Alert; onClose: () => void }) {
  const entries = Object.entries(alert.meta || {});
  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Alert detail</p>
          <h2 className="mt-2 text-2xl font-semibold">{alert.title}</h2>
        </div>
        <Button variant="ghost" onClick={onClose}>
          Close
        </Button>
      </div>
      <div className="mt-6 rounded-[24px] border border-border/70 bg-card/75 p-5">
        <p className="text-sm text-muted-foreground">{alert.description}</p>
        <div className="mt-4 grid gap-2">
          {entries.length === 0 ? (
            <p className="text-xs text-muted-foreground">No metadata for this alert.</p>
          ) : (
            entries.map(([key, value]) => (
              <div key={key} className="flex items-center justify-between rounded-xl border border-border/60 px-3 py-2 text-xs">
                <span className="uppercase tracking-[0.12em] text-muted-foreground">{key.replace(/_/g, " ")}</span>
                <span className="font-medium">{String(value)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
