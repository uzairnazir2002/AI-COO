"use client";

import { useMemo, useState } from "react";
import { Clock3, Mail, RefreshCcw, ShieldCheck, Workflow } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAdminRecompute, useAnalyticsRecompute, useCancelJob, useJobs, useOutbox, usePauseSchedule, useResumeSchedule, useRetryJob, useRetryOutboxEvent, useRunSchedule, useSystemStatus } from "@/features/activity/hooks";
import { isOwner } from "@/lib/auth/rbac";
import { formatDate } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";

const jobStatusVariant: Record<string, "default" | "secondary" | "warning" | "success" | "destructive"> = {
  PENDING: "secondary",
  RUNNING: "warning",
  RETRYING: "warning",
  SUCCEEDED: "success",
  FAILED: "destructive",
};

export default function ActivityPage() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((org) => org.org_id === s.selectedOrgId)?.role);
  const [status, setStatus] = useState("ALL");
  const [taskName, setTaskName] = useState("");
  const [page, setPage] = useState(1);
  const [outboxStatus, setOutboxStatus] = useState("ALL");
  const [outboxPage, setOutboxPage] = useState(1);
  const jobs = useJobs({ status: status === "ALL" ? undefined : status, task_name: taskName || undefined, page, page_size: 12 });
  const outbox = useOutbox({ status: outboxStatus === "ALL" ? undefined : outboxStatus, page: outboxPage, page_size: 8 });
  const systemStatus = useSystemStatus();
  const retryOutboxEvent = useRetryOutboxEvent();
  const retryJob = useRetryJob();
  const cancelJob = useCancelJob();
  const pauseSchedule = usePauseSchedule();
  const resumeSchedule = useResumeSchedule();
  const runSchedule = useRunSchedule();
  const analyticsRecompute = useAnalyticsRecompute();
  const adminRecompute = useAdminRecompute();
  const toast = useToast();

  const activeJobs = useMemo(
    () => jobs.data?.items.filter((item) => ["PENDING", "RUNNING", "RETRYING"].includes(item.status)).length ?? 0,
    [jobs.data?.items],
  );

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="No organization"
        title="Select an organization to inspect operational activity."
        description="Jobs, worker activity, recompute controls, and background automation are all org-scoped."
        actions={[{ label: "Go to organizations", href: "/app/orgs" }]}
      />
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Activity"
        description="Background jobs, recompute controls, and worker-backed automation visibility for the selected organization."
        actions={
          <>
            <Button variant="outline" onClick={() => void jobs.refetch()}>
              <RefreshCcw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Button
              variant="outline"
              disabled={analyticsRecompute.isPending}
              onClick={async () => {
                const result = await analyticsRecompute.mutateAsync();
                toast.toast({
                  title: "Analytics recompute queued",
                  description: `Alerts job ${result.alerts_job_id} and forecast job ${result.forecast_job_id} were enqueued.`,
                  variant: "success",
                });
              }}
            >
              Queue analytics recompute
            </Button>
            {isOwner(role) ? (
              <Button
                disabled={adminRecompute.isPending}
                onClick={async () => {
                  const result = await adminRecompute.mutateAsync();
                  toast.toast({
                    title: "Full org recompute queued",
                    description: `Started ${Object.keys(result.jobs).length} tracked admin jobs.`,
                    variant: "success",
                  });
                }}
              >
                Queue full org recompute
              </Button>
            ) : null}
          </>
        }
      />

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
              <p className="mt-2 text-2xl font-semibold">{jobs.data?.total ?? 0}</p>
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
              <Select value={status} onValueChange={(value) => { setStatus(value); setPage(1); }}>
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
              <Input value={taskName} onChange={(event) => { setTaskName(event.target.value); setPage(1); }} placeholder="recompute_alerts" />
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
          {(jobs.data?.items.length ?? 0) === 0 ? (
            <EmptyState
              eyebrow="No job records"
              title="No tracked jobs yet."
              description="Queue a recompute to populate this activity feed, or wait for worker tasks to write their next state transition."
            />
          ) : (
            jobs.data?.items.map((job) => (
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
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={async () => {
                          const result = await retryJob.mutateAsync(job.id);
                          toast.toast({ title: "Job re-queued", description: result.new_task_id ?? result.status, variant: "success" });
                        }}
                      >
                        Retry
                      </Button>
                    ) : null}
                    {["PENDING", "RUNNING", "RETRYING"].includes(job.status) ? (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={async () => {
                          const result = await cancelJob.mutateAsync(job.id);
                          toast.toast({ title: "Job cancelled", description: result.status, variant: "warning" });
                        }}
                      >
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
            <p className="text-sm text-muted-foreground">{jobs.data?.total ?? 0} total jobs</p>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
                Prev
              </Button>
              <span className="text-sm">Page {page}</span>
              <Button
                variant="outline"
                size="sm"
                disabled={Boolean(jobs.data && page * jobs.data.page_size >= jobs.data.total)}
                onClick={() => setPage((value) => value + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {isOwner(role) ? (
        <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <Card>
            <CardHeader>
              <CardTitle>Outbox monitor</CardTitle>
              <CardDescription>Owner-only visibility into queued, retrying, failed, and sent org email events.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <div className="w-40">
                  <Select
                    value={outboxStatus}
                    onValueChange={(value) => {
                      setOutboxStatus(value);
                      setOutboxPage(1);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All statuses</SelectItem>
                      <SelectItem value="PENDING">Pending</SelectItem>
                      <SelectItem value="PROCESSING">Processing</SelectItem>
                      <SelectItem value="RETRYING">Retrying</SelectItem>
                      <SelectItem value="FAILED">Failed</SelectItem>
                      <SelectItem value="SENT">Sent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {Object.entries(outbox.data?.counts_by_status ?? {}).map(([key, value]) => (
                  <Badge key={key} variant={key === "FAILED" ? "destructive" : key === "RETRYING" ? "warning" : "secondary"}>
                    {key}: {value}
                  </Badge>
                ))}
              </div>

              {(outbox.data?.items.length ?? 0) === 0 ? (
                <p className="text-sm text-muted-foreground">No outbox events for the selected organization and filter.</p>
              ) : (
                outbox.data?.items.map((event) => (
                  <div key={event.id} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="rounded-xl bg-primary/10 p-2 text-primary">
                          <Mail className="h-4 w-4" />
                        </div>
                        <div>
                          <p className="font-medium">{event.event_type}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            Created {formatDate(event.created_at)} | Attempts {event.attempts}/{event.max_attempts}
                          </p>
                        </div>
                      </div>
                      <Badge variant={event.status === "FAILED" ? "destructive" : event.status === "RETRYING" ? "warning" : event.status === "SENT" ? "success" : "secondary"}>
                        {event.status}
                      </Badge>
                    </div>
                    <pre className="mt-4 overflow-auto rounded-[18px] border border-border/60 bg-background/65 p-3 text-xs">
                      {JSON.stringify(event.payload ?? {}, null, 2)}
                    </pre>
                    {event.last_error ? <p className="mt-3 text-xs text-danger">{event.last_error}</p> : null}
                    {["FAILED", "RETRYING"].includes(event.status) ? (
                      <div className="mt-3 flex justify-end">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={retryOutboxEvent.isPending}
                          onClick={async () => {
                            await retryOutboxEvent.mutateAsync(event.id);
                            toast.toast({ title: "Outbox event re-queued", description: "The worker can pick it up on the next cycle.", variant: "success" });
                          }}
                        >
                          Retry delivery
                        </Button>
                      </div>
                    ) : null}
                  </div>
                ))
              )}

              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">{outbox.data?.total ?? 0} total outbox events</p>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" disabled={outboxPage <= 1} onClick={() => setOutboxPage((value) => value - 1)}>
                    Prev
                  </Button>
                  <span className="text-sm">Page {outboxPage}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={Boolean(outbox.data && outboxPage * outbox.data.page_size >= outbox.data.total)}
                    onClick={() => setOutboxPage((value) => value + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Scheduler admin</CardTitle>
              <CardDescription>Configured beat schedule plus recent system-wide worker jobs.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                {(systemStatus.data?.scheduler ?? []).map((entry) => (
                  <div key={entry.name} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium">{entry.name}</p>
                      <Badge variant={entry.paused ? "warning" : "outline"}>{entry.paused ? "Paused" : "Scheduled"}</Badge>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">{entry.task}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{entry.schedule}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {entry.paused ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            await resumeSchedule.mutateAsync(entry.name);
                            toast.toast({ title: "Schedule resumed", description: entry.name, variant: "success" });
                          }}
                        >
                          Resume
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            await pauseSchedule.mutateAsync(entry.name);
                            toast.toast({ title: "Schedule paused", description: entry.name, variant: "warning" });
                          }}
                        >
                          Pause
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={async () => {
                          const result = await runSchedule.mutateAsync(entry.name);
                          toast.toast({ title: "Schedule dispatched", description: result.task_id, variant: "success" });
                        }}
                      >
                        Run now
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                <p className="text-xs uppercase text-muted-foreground">Recent system jobs</p>
                <div className="mt-3 space-y-3">
                  {(systemStatus.data?.system_jobs ?? []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">No system-scoped worker jobs tracked yet.</p>
                  ) : (
                    systemStatus.data?.system_jobs.map((job) => (
                      <div key={job.id} className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm font-medium">{job.task_name}</p>
                          <Badge variant={job.status === "FAILED" ? "destructive" : job.status === "SUCCEEDED" ? "success" : "secondary"}>
                            {job.status}
                          </Badge>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">Updated {formatDate(job.updated_at)}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
