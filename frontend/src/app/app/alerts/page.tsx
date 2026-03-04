"use client";

import { useMemo, useState } from "react";

import { AlertCard } from "@/components/common/alert-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/components/common/use-toast";
import { useAlerts, useDismissAlert } from "@/features/alerts/hooks";

export default function AlertsPage() {
  const [status, setStatus] = useState<"open" | "dismissed">("open");
  const [kind, setKind] = useState("ALL");
  const alerts = useAlerts(status);
  const dismiss = useDismissAlert();
  const toast = useToast();

  const filtered = useMemo(() => {
    const items = alerts.data?.items ?? [];
    return kind === "ALL" ? items : items.filter((a) => a.kind === kind);
  }, [alerts.data?.items, kind]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="mr-auto text-2xl font-semibold">Alerts</h1>
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
      </div>

      {filtered.length === 0 ? (
        <Card>
          <CardHeader><CardTitle>No alerts</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">No alerts found. Add transactions to activate detection.</p>
            <Button className="mt-3" variant="outline" onClick={() => (window.location.href = "/app/transactions")}>Add transactions</Button>
          </CardContent>
        </Card>
      ) : null}

      {filtered.map((alert) => (
        <AlertCard
          key={alert.id}
          alert={alert}
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
    </div>
  );
}
