"use client";

import { BellRing } from "lucide-react";

import { AlertCard } from "@/components/common/alert-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Alert } from "@/types/domain";

const severityOrder: Array<Alert["severity"]> = ["HIGH", "MEDIUM", "LOW"];

export function AlertFeedPanel({
  alerts,
  maxImpact,
  assigneeLabelById,
  onOpenAlert,
  onDismiss,
}: {
  alerts: Alert[];
  maxImpact: number;
  assigneeLabelById: (id: string | null | undefined) => string | null;
  onOpenAlert: (id: string) => void;
  onDismiss?: (id: string) => Promise<void>;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BellRing className="h-4 w-4 text-primary" />
          Alert feed
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {severityOrder.map((severity) => {
          const items = alerts.filter((alert) => alert.severity === severity);
          if (items.length === 0) return null;
          return (
            <section key={severity} className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">{severity} severity</p>
              <div className="space-y-2">
                {items.map((alert) => (
                  <AlertCard
                    key={alert.id}
                    alert={alert}
                    maxImpact={maxImpact}
                    assigneeLabel={assigneeLabelById(alert.assigned_to_user_id)}
                    onOpen={onOpenAlert}
                    onDismiss={onDismiss}
                  />
                ))}
              </div>
            </section>
          );
        })}
      </CardContent>
    </Card>
  );
}
