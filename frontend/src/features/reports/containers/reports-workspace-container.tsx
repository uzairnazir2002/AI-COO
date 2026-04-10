"use client";

import { EmptyState } from "@/components/common/empty-state";
import { ProgressiveDisclosure } from "@/components/common/progressive-disclosure";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { RightRail } from "@/components/layout/right-rail";
import { StatusStrip } from "@/components/layout/status-strip";
import { ReportJobStatusPanel } from "@/components/reports/report-job-status-panel";
import { ReportHistoryList } from "@/components/reports/report-history-list";
import { LatestReportCard } from "@/components/reports/latest-report-card";
import { ReportPreviewFrame } from "@/components/reports/report-preview-frame";
import { ScheduleReportCard } from "@/components/reports/schedule-report-card";
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
  editable,
  onDownload,
  previewUrl,
  jobs,
  trackedJob,
  jobsLoading,
  formatDate,
  onSchedule,
  lastGeneration,
}: {
  statusItems: StatusItem[];
  reports: Report[];
  onGenerate: () => void;
  editable: boolean;
  onDownload: (reportId: string) => Promise<void>;
  previewUrl: string | null;
  jobs: ReportJobRow[];
  trackedJob?: ReportJobRow;
  jobsLoading?: boolean;
  formatDate: (value?: string | null) => string;
  onSchedule: () => void;
  lastGeneration?: { jobId: string; status: string; reused: boolean; reportId?: string | null };
}) {
  const latestReport = reports[0] ?? null;

  return (
    <>
      <StatusStrip items={statusItems} />

      <div className="grid gap-4 xl:grid-cols-[1fr_1.25fr_0.8fr]">
        <Panel>
          <PanelHeader>
            <h2 className="text-base font-semibold">Latest report</h2>
          </PanelHeader>
          <PanelBody className="space-y-3">
            {reports.length === 0 ? (
              <EmptyState
                eyebrow="No reports"
                title="Generate your first report."
                description="Weekly reports are generated against the current organization and remain idempotent when regenerated for the same week."
                actions={editable ? [{ label: "Generate report", onClick: onGenerate }] : []}
              />
            ) : (
              <>
                {latestReport ? (
                  <LatestReportCard report={latestReport} formatDate={formatDate} onDownload={onDownload} onGenerate={onGenerate} />
                ) : null}
                <ReportHistoryList reports={reports} formatDate={formatDate} />
              </>
            )}
          </PanelBody>
        </Panel>

        <Panel>
          <PanelBody>
            <ReportPreviewFrame previewUrl={previewUrl} />
          </PanelBody>
        </Panel>

        <RightRail className="xl:col-start-3" sticky>
          <ScheduleReportCard onSchedule={onSchedule} />
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Metadata & sharing</h2>
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
          <ProgressiveDisclosure title="Show generation details" hideLabel="Hide generation details">
            <Panel>
              <PanelHeader>
                <h2 className="text-base font-semibold">Recent report jobs</h2>
              </PanelHeader>
              <PanelBody className="space-y-3">
                <ReportJobStatusPanel jobs={jobs} trackedJob={trackedJob} formatDate={formatDate} jobsLoading={jobsLoading} />
              </PanelBody>
            </Panel>
          </ProgressiveDisclosure>
        </RightRail>
      </div>
    </>
  );
}
