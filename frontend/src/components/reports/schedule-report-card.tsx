"use client";

import { CalendarClock } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ScheduleReportCard({
  onSchedule,
  description,
}: {
  onSchedule: () => void;
  description?: string;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card/75 p-4" data-testid="schedule-report-card">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Schedule</p>
      <p className="mt-2 text-sm font-medium">Weekly report cadence</p>
      <p className="mt-1 text-xs text-muted-foreground">
        {description || "Configure recurring report generation and delivery preferences for this organization."}
      </p>
      <Button className="mt-3" size="sm" variant="outline" onClick={onSchedule}>
        <CalendarClock className="mr-2 h-4 w-4" />
        Configure schedule
      </Button>
    </div>
  );
}
