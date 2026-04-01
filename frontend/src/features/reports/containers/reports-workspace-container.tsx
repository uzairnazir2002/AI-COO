"use client";

import { Download } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { RightRail } from "@/components/layout/right-rail";
import { StatusStrip } from "@/components/layout/status-strip";
import { ReportJobStatusPanel } from "@/components/reports/report-job-status-panel";
import { ReportPreviewFrame } from "@/components/reports/report-preview-frame";
import { ScheduleReportCard } from "@/components/reports/schedule-report-card";
import { Button } from "@/components/ui/button";
import type { Report } from "@/types/domain";

type StatusItem = { label: string; value: string; tone: "neutral" | "live" | "warning" | "danger" };

type ReportJobRow = {
  id: string;
  status: string;
  task_name: string;
  updated_at: string;
};

export function ReportsWorkspaceContainer({
  statusItems,
  reports,
  onGenerate,
  onDownload,
  previewUrl,
  jobs,
  trackedJob,
  formatDate,
  onSchedule,
  lastGeneration,
}: {
  statusItems: StatusItem[];
  reports: Report[];
  onGenerate: () => void;
  onDownload: (reportId: string) => Promise<void>;
  previewUrl: string | null;
  jobs: ReportJobRow[];
  trackedJob?: ReportJobRow;
  formatDate: (value?: string | null) => string;
  onSchedule: () => void;
  lastGeneration?: { jobId: string; status: string; reused: boolean; reportId?: string | null };
}) {
  return (
    <>
      <StatusStrip items={statusItems} />

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.2fr_0.85fr]">
        <Panel>
          <PanelHeader>
            <h2 className="text-base font-semibold">Report history</h2>
          </PanelHeader>
          <PanelBody className="space-y-3">
            {reports.length === 0 ? (
              <EmptyState
                eyebrow="No reports"
                title="Generate your first report."
                description="Weekly reports are generated against the current organization and remain idempotent when regenerated for the same week."
                actions={[{ label: "Generate report", onClick: onGenerate }]}
              />
            ) : (
              reports.map((report) => (
                <div key={report.id} className="rounded-2xl border border-border/70 bg-card/70 p-4">
                  <p className="font-medium">{formatDate(report.week_start)} - {formatDate(report.week_end)}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Created {formatDate(report.created_at)}</p>
                  <Button className="mt-3" variant="outline" size="sm" onClick={() => void onDownload(report.id)}>
                    <Download className="mr-2 h-4 w-4" />
                    Download
                  </Button>
                </div>
              ))
            )}
          </PanelBody>
        </Panel>

        <Panel>
          <PanelBody>
            <ReportPreviewFrame previewUrl={previewUrl} />
          </PanelBody>
        </Panel>

        <RightRail className="xl:col-start-3" sticky>
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Recent report jobs</h2>
            </PanelHeader>
            <PanelBody className="space-y-3">
              <ReportJobStatusPanel jobs={jobs} trackedJob={trackedJob} formatDate={formatDate} />
            </PanelBody>
          </Panel>
          <ScheduleReportCard onSchedule={onSchedule} />
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Report metadata & sharing</h2>
            </PanelHeader>
            <PanelBody className="space-y-2 text-sm">
              <p className="text-muted-foreground">
                Preview URL: {previewUrl ? "Available" : "Not loaded"}
              </p>
              {lastGeneration ? (
                <div className="rounded-xl border border-border/70 bg-card/70 p-3 text-xs text-muted-foreground">
                  <p>Latest generation status: <span className="font-medium text-foreground">{lastGeneration.status}</span></p>
                  <p>Tracked job: {lastGeneration.jobId}</p>
                  <p>Reuse behavior: {lastGeneration.reused ? `Reused report ${lastGeneration.reportId ?? ""}` : "Generated a new report job"}</p>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">Generate a report to see metadata and reuse details.</p>
              )}
            </PanelBody>
          </Panel>
        </RightRail>
      </div>
    </>
  );
}
