"use client";

import { Badge } from "@/components/ui/badge";

type ReportJob = {
  id: string;
  task_name: string;
  status: string;
  updated_at: string;
};

export function ReportJobStatusPanel({
  jobs,
  trackedJob,
  formatDate,
  jobsLoading = false,
}: {
  jobs: ReportJob[];
  trackedJob?: ReportJob;
  formatDate: (value: string) => string;
  jobsLoading?: boolean;
}) {
  if (jobsLoading) {
    return <p className="text-sm text-muted-foreground">Loading generation jobs…</p>;
  }

  return (
    <div className="space-y-3">
      {jobs.length === 0 ? (
        <p className="text-sm text-muted-foreground">No tracked report-generation jobs yet.</p>
      ) : (
        jobs.map((job) => (
          <div key={job.id} className="rounded-2xl border border-border/70 bg-card/70 p-3">
            <p className="font-medium">{job.task_name}</p>
            <p className="mt-1 text-xs text-muted-foreground">Updated {formatDate(job.updated_at)}</p>
            <Badge className="mt-2" variant={job.status === "FAILED" ? "destructive" : job.status === "SUCCEEDED" ? "success" : "secondary"}>
              {job.status}
            </Badge>
          </div>
        ))
      )}

      {trackedJob ? (
        <div className="rounded-2xl border border-border/70 bg-card/70 p-3 text-sm text-muted-foreground">
          {trackedJob.status === "FAILED" ? (
            <span>Tracked job failed. Check Activity for retry details.</span>
          ) : trackedJob.status === "SUCCEEDED" ? (
            <span>Tracked job completed successfully.</span>
          ) : trackedJob.status === "RUNNING" ? (
            <span>Tracked job is running.</span>
          ) : (
            <span>Tracked job is queued.</span>
          )}
        </div>
      ) : null}
    </div>
  );
}

