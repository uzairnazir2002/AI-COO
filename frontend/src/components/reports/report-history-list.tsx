"use client";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import type { Report } from "@/types/domain";

export function ReportHistoryList({
  reports,
  formatDate,
}: {
  reports: Report[];
  formatDate: (value?: string | null) => string;
}) {
  return (
    <Panel className="rounded-2xl">
      <PanelHeader>
        <h3 className="text-sm font-semibold">History</h3>
      </PanelHeader>
      <PanelBody className="space-y-2">
        {reports.slice(0, 8).map((report) => (
          <div key={report.id} className="rounded-xl border border-border/70 bg-card/70 px-3 py-2">
            <p className="text-sm font-medium">{formatDate(report.week_start)} - {formatDate(report.week_end)}</p>
            <p className="text-xs text-muted-foreground">Created {formatDate(report.created_at)}</p>
          </div>
        ))}
      </PanelBody>
    </Panel>
  );
}

