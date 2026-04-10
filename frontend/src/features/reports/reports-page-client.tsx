"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { LoaderCircle, Sparkles } from "lucide-react";

import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { InlineErrorBanner } from "@/components/states/inline-error-banner";
import { RetryCard } from "@/components/states/retry-card";
import { SkeletonPanel } from "@/components/states/skeleton-panel";
import { SuccessStateCard } from "@/components/states/success-state-card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useJobs } from "@/features/activity/hooks";
import { ReportsWorkspaceContainer } from "@/features/reports/containers/reports-workspace-container";
import { fetchReportDownload, useGenerateReport, useReports } from "@/features/reports/hooks";
import { canEdit } from "@/lib/auth/rbac";
import { formatDate, weekStartISO } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";

export function ReportsPageClient() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const selectedLocationId = useAppStore((s) => s.selectedLocationId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const editable = canEdit(role);
  const reports = useReports();
  const generate = useGenerateReport();
  const toast = useToast();
  const [weekStart, setWeekStart] = useState(weekStartISO());
  const [dialogOpen, setDialogOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [lastQueuedJobId, setLastQueuedJobId] = useState<string | null>(null);
  const [lastGeneration, setLastGeneration] = useState<{ jobId: string; status: string; reused: boolean; reportId?: string | null } | null>(null);
  const router = useRouter();
  const reportJobs = useJobs({ task_name: "generate_weekly_report", page: 1, page_size: 5 });
  const trackedJob = reportJobs.data?.items.find((job) => job.task_id === lastQueuedJobId);
  const reportJobRows = (reportJobs.data?.items ?? []).map((job) => ({
    id: job.task_id,
    task_name: job.task_name,
    status: job.status,
    updated_at: job.updated_at || job.created_at,
  }));
  const trackedJobRow = trackedJob
    ? {
        id: trackedJob.task_id,
        task_name: trackedJob.task_name,
        status: trackedJob.status,
        updated_at: trackedJob.updated_at || trackedJob.created_at,
      }
    : undefined;

  useEffect(() => {
    if (typeof window === "undefined") return;
    const searchParams = new URLSearchParams(window.location.search);
    if (searchParams.get("action") !== "generate") return;
    setDialogOpen(true);
    router.replace("/app/reports");
  }, [router]);

  const statusItems = useMemo(() => {
    const items: Array<{ label: string; value: string; tone: "neutral" | "live" | "warning" | "danger" }> = [];
    if (generate.isPending) {
      items.push({ label: "Generation", value: "running", tone: "warning" });
    }
    if (trackedJob) {
      const tone =
        trackedJob.status === "FAILED"
          ? "danger"
          : trackedJob.status === "SUCCEEDED"
            ? "live"
            : "warning";
      items.push({ label: "Tracked job", value: trackedJob.status.toLowerCase(), tone });
    }
    return items;
  }, [generate.isPending, trackedJob]);

  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Reports"
        title="Reports"
        description="Generate, monitor, and distribute weekly reports with reliable async status tracking."
        scopeChips={[`Week start: ${weekStart}`, selectedLocationId ? "Location scope: filtered" : "Location scope: all"]}
        actions={
          <>
            <Button variant="outline" onClick={() => toast.toast({ title: "Scheduling is coming soon", variant: "default" })}>
              Schedule weekly
            </Button>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button disabled={!editable} title={!editable ? "Viewer role cannot generate reports" : undefined}>
                  Generate report
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Generate weekly report</DialogTitle>
                  <DialogDescription>
                    Generation is tracked as a job and reflected in activity history for the current organization.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <Input type="date" value={weekStart} onChange={(e) => setWeekStart(e.target.value)} className="w-full sm:w-56" />
                  <Button
                    disabled={generate.isPending || !editable}
                    onClick={async () => {
                      try {
                        const result = await generate.mutateAsync(weekStart);
                        setLastQueuedJobId(result.job_id);
                        setLastGeneration({
                          jobId: result.job_id,
                          status: result.status,
                          reused: Boolean(result.report_id),
                          reportId: result.report_id,
                        });
                        toast.toast({
                          title: result.report_id ? "Report already available" : "Report generation requested",
                          description: result.report_id
                            ? `Reused existing report ${result.report_id}.`
                            : `Job ${result.job_id} is ${result.status.toLowerCase()}.`,
                          variant: result.report_id ? "success" : "default",
                        });
                        setDialogOpen(false);
                      } catch (error) {
                        toast.toast({
                          title: "Report generation failed",
                          description: error instanceof Error ? error.message : "Request failed.",
                          variant: "danger",
                        });
                      }
                    }}
                  >
                    {generate.isPending ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                    Generate / Regenerate
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </>
        }
      />

      {reports.isLoading && !reports.data ? <SkeletonPanel rows={5} /> : null}

      {reports.error || reportJobs.error ? (
        <div className="space-y-3">
          <InlineErrorBanner
            message={String(
              (reports.error as Error | undefined)?.message
              || (reportJobs.error as Error | undefined)?.message
              || "Unable to load reports workspace.",
            )}
          />
          <RetryCard
            message="Retry loading reports and generation jobs."
            onRetry={() => {
              void reports.refetch();
              void reportJobs.refetch();
            }}
          />
        </div>
      ) : null}

      {lastGeneration && lastGeneration.status !== "FAILED" ? (
        <SuccessStateCard
          title={lastGeneration.reused ? "Report reused" : "Report generation queued"}
          description={lastGeneration.reused
            ? `Existing report ${lastGeneration.reportId ?? ""} was reused.`
            : `Tracking job ${lastGeneration.jobId} (${lastGeneration.status.toLowerCase()}).`}
        />
      ) : null}

      <ReportsWorkspaceContainer
        statusItems={statusItems}
        reports={reports.data?.items ?? []}
        onGenerate={() => setDialogOpen(true)}
        editable={editable}
        onDownload={async (reportId) => {
          if (!orgId) return;
          const dl = await fetchReportDownload(reportId, orgId, selectedLocationId);
          if (dl.url) {
            window.open(dl.url, "_blank", "noopener,noreferrer");
            setPreviewUrl(dl.url);
          } else {
            toast.toast({ title: "Download unavailable", description: "The backend did not return a report URL.", variant: "danger" });
          }
        }}
        previewUrl={previewUrl}
        jobs={reportJobRows}
        trackedJob={trackedJobRow}
        jobsLoading={Boolean(orgId) && reportJobs.isPending}
        formatDate={(value) => formatDate(value || "")}
        onSchedule={() => toast.toast({ title: "Scheduling is coming soon", variant: "default" })}
        lastGeneration={lastGeneration ?? undefined}
      />
    </div>
  );
}
