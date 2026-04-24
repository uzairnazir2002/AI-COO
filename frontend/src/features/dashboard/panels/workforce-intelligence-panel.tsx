"use client";

import Link from "next/link";
import { Users } from "lucide-react";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { WorkforceDashboardIntelResponse } from "@/lib/api/schemas";

export function WorkforceIntelligencePanel({
  loading,
  error,
  intel,
  reportsHref,
}: {
  loading: boolean;
  error: unknown;
  intel: WorkforceDashboardIntelResponse | null | undefined;
  reportsHref: string;
}) {
  return (
    <Panel>
      <PanelHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 rounded-2xl bg-primary/10 p-2 text-primary">
              <Users className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">Workforce signal</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Live org snapshot for attendance, leave, payroll, and people risk (Phase 7 intelligence).
              </p>
            </div>
          </div>
          <Button asChild variant="outline" size="sm" className="sm:shrink-0">
            <Link href={reportsHref}>Workforce summary JSON</Link>
          </Button>
        </div>
      </PanelHeader>
      <PanelBody className="space-y-3">
        {error ? (
          <p className="text-sm text-destructive">
            Could not load workforce intelligence.{" "}
            <span className="text-muted-foreground">{(error as Error)?.message || "Request failed."}</span>
          </p>
        ) : null}
        {loading && !intel ? (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-xl" />
            ))}
          </div>
        ) : null}
        {intel ? (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-border/60 bg-muted/30 px-3 py-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Today (as of)</p>
                <p className="text-lg font-semibold text-foreground">{intel.as_of}</p>
                <p className="text-xs text-muted-foreground">
                  Present {intel.present_today} · Absent {intel.absent_today} · Late {intel.late_today}
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 px-3 py-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Leave</p>
                <p className="text-lg font-semibold text-foreground">{intel.pending_leave_requests}</p>
                <p className="text-xs text-muted-foreground">Pending requests</p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 px-3 py-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Payroll</p>
                <p className="text-lg font-semibold text-foreground">{intel.payroll_due_periods}</p>
                <p className="text-xs text-muted-foreground">
                  Periods due (7d) · {intel.unpaid_payroll_entries} unpaid entries
                </p>
              </div>
              <div className="rounded-xl border border-border/60 bg-muted/30 px-3 py-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">People</p>
                <p className="text-xs text-muted-foreground">
                  Contracts (30d): {intel.contract_expiring_soon} · Probation ending: {intel.probation_ending_soon}
                </p>
                <p className="text-xs text-muted-foreground">Announcements to ack: {intel.unacknowledged_announcements}</p>
              </div>
            </div>
            {intel.top_risks.length > 0 ? (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-3 py-2">
                <p className="text-xs font-medium uppercase tracking-wide text-amber-900 dark:text-amber-200">Top risks</p>
                <ul className="mt-1 list-inside list-disc text-sm text-foreground">
                  {intel.top_risks.slice(0, 5).map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No workforce risk flags for this snapshot.</p>
            )}
          </>
        ) : null}
      </PanelBody>
    </Panel>
  );
}
