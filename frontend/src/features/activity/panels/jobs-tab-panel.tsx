"use client";

import { Clock3, ShieldCheck, Workflow } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatDate } from "@/lib/utils/format";
import type { Job, Role } from "@/types/domain";

const jobStatusVariant: Record<string, "default" | "secondary" | "warning" | "success" | "destructive"> = {
  PENDING: "secondary",
  RUNNING: "warning",
  RETRYING: "warning",
  SUCCEEDED: "success",
  FAILED: "destructive",
};

export function JobsTabPanel({
  role,
  activeJobs,
  jobsTotal,
  status,
  setStatus,
  taskName,
  setTaskName,
  jobs,
  page,
  pageSize,
  onPrevPage,
  onNextPage,
  onRetryJob,
  onCancelJob,
}: {
  role?: Role;
  activeJobs: number;
  jobsTotal: number;
  status: string;
  setStatus: (value: string) => void;
  taskName: string;
  setTaskName: (value: string) => void;
  jobs: Job[];
  page: number;
  pageSize: number;
  onPrevPage: () => void;
  onNextPage: () => void;
  onRetryJob: (jobId: string) => Promise<void>;
  onCancelJob: (jobId: string) => Promise<void>;
}) {
  return (
    <section id="activity-jobs" className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Live queue snapshot</CardTitle>
            <CardDescription>Job lifecycle tracking from the backend `job_states` table.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
            <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
              <p className="text-xs uppercase text-muted-foreground">Active jobs</p>
              <p className="mt-2 text-2xl font-semibold">{activeJobs}</p>
            </div>
            <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
              <p className="text-xs uppercase text-muted-foreground">Tracked rows</p>
              <p className="mt-2 text-2xl font-semibold">{jobsTotal}</p>
            </div>
            <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
              <p className="text-xs uppercase text-muted-foreground">Access</p>
              <p className="mt-2 text-sm font-semibold">{role ?? "Unknown role"}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Worker automation</CardTitle>
            <CardDescription>Scheduled and outbox-backed tasks now surfaced in-app.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <div className="flex items-start gap-3 rounded-[22px] border border-border/70 bg-card/70 p-4">
              <Workflow className="mt-0.5 h-4 w-4 text-primary" />
              <div>
                <p className="font-medium text-foreground">Tracked recomputes</p>
                <p className="mt-1">Forecast, alert, monthly aggregate, and report object verification jobs are visible here once queued.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-[22px] border border-border/70 bg-card/70 p-4">
              <Clock3 className="mt-0.5 h-4 w-4 text-primary" />
              <div>
                <p className="font-medium text-foreground">Scheduled worker cadence</p>
                <p className="mt-1">Beat-driven report generation and outbox processing continue on the worker even when the UI is idle.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-[22px] border border-border/70 bg-card/70 p-4">
              <ShieldCheck className="mt-0.5 h-4 w-4 text-primary" />
              <div>
                <p className="font-medium text-foreground">RBAC-aware visibility</p>
                <p className="mt-1">Viewer access sees safe metadata only. Owners unlock the full org recompute control surface.</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
            <CardDescription>Narrow the tracked-job view without leaving the screen.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <p className="text-xs uppercase text-muted-foreground">Status</p>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All statuses</SelectItem>
                  <SelectItem value="PENDING">Pending</SelectItem>
                  <SelectItem value="RUNNING">Running</SelectItem>
                  <SelectItem value="RETRYING">Retrying</SelectItem>
                  <SelectItem value="SUCCEEDED">Succeeded</SelectItem>
                  <SelectItem value="FAILED">Failed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <p className="text-xs uppercase text-muted-foreground">Task name</p>
              <Input value={taskName} onChange={(event) => setTaskName(event.target.value)} placeholder="recompute_alerts" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Tracked jobs</CardTitle>
          <CardDescription>Most recent job state transitions for this organization.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {jobs.length === 0 ? (
            <EmptyState
              eyebrow="No job records"
              title="No tracked jobs yet."
              description="Queue a recompute to populate this activity feed, or wait for worker tasks to write their next state transition."
            />
          ) : (
            jobs.map((job) => (
              <div key={job.id} className="rounded-[24px] border border-border/70 bg-card/70 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium">{job.task_name}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Created {formatDate(job.created_at)} | Updated {formatDate(job.updated_at)} | Retry count {job.retry_count}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={jobStatusVariant[job.status] ?? "secondary"}>{job.status}</Badge>
                    <Badge variant="outline">{job.progress}%</Badge>
                    {["FAILED", "CANCELLED"].includes(job.status) ? (
                      <Button size="sm" variant="outline" onClick={() => void onRetryJob(job.id)}>
                        Retry
                      </Button>
                    ) : null}
                    {["PENDING", "RUNNING", "RETRYING"].includes(job.status) ? (
                      <Button size="sm" variant="outline" onClick={() => void onCancelJob(job.id)}>
                        Cancel
                      </Button>
                    ) : null}
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                    <p className="text-xs uppercase text-muted-foreground">Payload</p>
                    <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(job.payload ?? {}, null, 2)}</pre>
                  </div>
                  <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                    <p className="text-xs uppercase text-muted-foreground">Result</p>
                    <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(job.result ?? {}, null, 2)}</pre>
                    {job.last_error ? <p className="mt-3 text-xs text-danger">{job.last_error}</p> : null}
                    {job.traceback_summary ? <p className="mt-1 text-xs text-muted-foreground">{job.traceback_summary}</p> : null}
                  </div>
                </div>
              </div>
            ))
          )}

          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">{jobsTotal} total jobs</p>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={onPrevPage}>
                Prev
              </Button>
              <span className="text-sm">Page {page}</span>
              <Button variant="outline" size="sm" disabled={Boolean(page * pageSize >= jobsTotal)} onClick={onNextPage}>
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

