"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Download, LoaderCircle, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useJobs } from "@/features/activity/hooks";
import { fetchReportDownload, useGenerateReport, useReports } from "@/features/reports/hooks";
import { formatDate, weekStartISO } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";

export function ReportsPageClient() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const selectedLocationId = useAppStore((s) => s.selectedLocationId);
  const reports = useReports();
  const generate = useGenerateReport();
  const toast = useToast();
  const [weekStart, setWeekStart] = useState(weekStartISO());
  const [dialogOpen, setDialogOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [lastQueuedJobId, setLastQueuedJobId] = useState<string | null>(null);
  const router = useRouter();
  const reportJobs = useJobs({ task_name: "generate_weekly_report", page: 1, page_size: 5 });
  const trackedJob = reportJobs.data?.items.find((job) => job.task_id === lastQueuedJobId);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const searchParams = new URLSearchParams(window.location.search);
    if (searchParams.get("action") !== "generate") return;
    setDialogOpen(true);
    router.replace("/app/reports");
  }, [router]);

  return (
    <div className="space-y-4">
      <SectionHeader
        title="Reports"
        description="Generate, regenerate, and download weekly reports with backend-compatible progress fallback."
        actions={
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>Generate report</Button>
            </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Generate weekly report</DialogTitle>
                  <DialogDescription>Generation is tracked as a job and reflected in activity history for the current organization.</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <Input type="date" value={weekStart} onChange={(e) => setWeekStart(e.target.value)} className="w-56" />
                  <Button
                    disabled={generate.isPending}
                    onClick={async () => {
                      const result = await generate.mutateAsync(weekStart);
                      setLastQueuedJobId(result.job_id);
                      toast.toast({
                        title: result.report_id ? "Report already available" : "Report generation requested",
                        description: result.report_id
                          ? `Reused existing report ${result.report_id}.`
                          : `Job ${result.job_id} is ${result.status.toLowerCase()}.`,
                        variant: result.report_id ? "success" : "default",
                      });
                      setDialogOpen(false);
                    }}
                  >
                  {generate.isPending ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                  Generate / Regenerate
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        }
      />

      {generate.isPending ? (
        <Card>
          <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
            <LoaderCircle className="h-4 w-4 animate-spin" />
            Generating report. This view will refresh from the existing reports endpoint once the request completes.
          </CardContent>
        </Card>
      ) : null}
      {!generate.isPending && trackedJob ? (
        <Card>
          <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
            {trackedJob.status === "FAILED" ? (
              <>
                <Badge variant="destructive">failed</Badge>
                Report generation failed. Check Activity for retry details.
              </>
            ) : trackedJob.status === "SUCCEEDED" ? (
              <>
                <Badge variant="success">completed</Badge>
                Report generation completed.
              </>
            ) : trackedJob.status === "RUNNING" ? (
              <>
                <LoaderCircle className="h-4 w-4 animate-spin" />
                Report is generating.
              </>
            ) : (
              <>
                <Badge variant="secondary">queued</Badge>
                Report job is queued.
              </>
            )}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader><CardTitle>Generated reports</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {(reports.data?.items.length ?? 0) === 0 ? (
            <EmptyState
              eyebrow="No reports"
              title="Generate your first report."
              description="Weekly reports are generated against the current organization and remain idempotent when regenerated for the same week."
              actions={[{ label: "Generate report", onClick: () => setDialogOpen(true) }]}
            />
          ) : (
            (reports.data?.items ?? []).map((report) => (
              <div key={report.id} className="flex items-center justify-between rounded-[22px] border border-border/70 bg-card/70 p-4">
                <div>
                  <p className="font-medium">{formatDate(report.week_start)} - {formatDate(report.week_end)}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Created {formatDate(report.created_at)}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    if (!orgId) return;
                    const dl = await fetchReportDownload(report.id, orgId, selectedLocationId);
                    if (dl.url) {
                      window.open(dl.url, "_blank", "noopener,noreferrer");
                      setPreviewUrl(dl.url);
                    } else {
                      toast.toast({ title: "Download unavailable", description: "The backend did not return a report URL.", variant: "danger" });
                    }
                  }}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Recent report jobs</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {(reportJobs.data?.items.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">No tracked report-generation jobs yet.</p>
          ) : (
            reportJobs.data?.items.map((job) => (
              <div key={job.id} className="flex items-center justify-between rounded-[22px] border border-border/70 bg-card/70 p-4">
                <div>
                  <p className="font-medium">{job.task_name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Updated {formatDate(job.updated_at)}</p>
                </div>
                <Badge variant={job.status === "FAILED" ? "destructive" : job.status === "SUCCEEDED" ? "success" : "secondary"}>
                  {job.status}
                </Badge>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {previewUrl ? (
        <Card>
          <CardHeader><CardTitle>PDF Preview</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">Preview depends on browser support for signed PDF URLs. If blocked, use Download.</p>
            <div className="h-[640px] overflow-hidden rounded-2xl border border-border">
              <iframe title="Report preview" src={previewUrl} className="h-full w-full" />
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
