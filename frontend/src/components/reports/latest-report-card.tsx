"use client";

import { Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Panel, PanelBody } from "@/components/layout/panel";
import type { Report } from "@/types/domain";

export function LatestReportCard({
  report,
  formatDate,
  onDownload,
  onGenerate,
}: {
  report: Report | null;
  formatDate: (value?: string | null) => string;
  onDownload: (reportId: string) => Promise<void>;
  onGenerate: () => void;
}) {
  if (!report) return null;

  return (
    <Panel className="rounded-2xl border-border/70 bg-card/70">
      <PanelBody className="p-4">
        <p className="font-medium">{formatDate(report.week_start)} - {formatDate(report.week_end)}</p>
        <p className="mt-1 text-xs text-muted-foreground">Created {formatDate(report.created_at)}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => void onDownload(report.id)}>
            <Download className="mr-2 h-4 w-4" />
            Download latest
          </Button>
          <Button size="sm" onClick={onGenerate}>Generate new</Button>
        </div>
      </PanelBody>
    </Panel>
  );
}

