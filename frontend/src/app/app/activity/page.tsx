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
import {
  useAdminRecompute,
  useAuditExport,
  useAnalyticsRecompute,
  useCancelJob,
  useDeletionRequests,
  useDeadLetter,
  useDismissDeadLetter,
  useJobs,
  useOutbox,
  useReplayDeadLetter,
  useRuntimeMetrics,
  usePauseSchedule,
  useRotateOrgPii,
  useResumeSchedule,
  useRetryJob,
  useRetryOutboxEvent,
  useRunSchedule,
  useRuntimeSlos,
  useSystemStatus,
} from "@/features/activity/hooks";
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
  const deletionRequests = useDeletionRequests();
  const systemStatus = useSystemStatus();
  const runtimeSlos = useRuntimeSlos();
  const runtimeMetrics = useRuntimeMetrics();
  const [deadLetterStatus, setDeadLetterStatus] = useState("OPEN");
  const [deadLetterPage, setDeadLetterPage] = useState(1);
  const deadLetter = useDeadLetter({ status: deadLetterStatus === "ALL" ? undefined : deadLetterStatus, page: deadLetterPage, page_size: 8 });
  const replayDeadLetter = useReplayDeadLetter();
  const dismissDeadLetter = useDismissDeadLetter();
  const retryOutboxEvent = useRetryOutboxEvent();
  const retryJob = useRetryJob();
  const cancelJob = useCancelJob();
  const rotateOrgPii = useRotateOrgPii();
  const auditExport = useAuditExport();
  const pauseSchedule = usePauseSchedule();
  const resumeSchedule = useResumeSchedule();
  const runSchedule = useRunSchedule();
  const analyticsRecompute = useAnalyticsRecompute();
  const adminRecompute = useAdminRecompute();
  const toast = useToast();
  const [auditSince, setAuditSince] = useState("");
  const [auditUntil, setAuditUntil] = useState("");

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
                  description: `Job ${result.job_id} is ${result.status.toLowerCase()}.`,
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
        <Card>
          <CardHeader>
            <CardTitle>Security & compliance</CardTitle>
            <CardDescription>
              Owner-only controls for immutable audit export and organization PII key rotation workflows.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 xl:grid-cols-2">
            <div className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-3">
              <p className="text-sm font-medium">Audit export</p>
              <p className="text-xs text-muted-foreground">
                Download NDJSON audit logs for an org-scoped time range. Export includes integrity checksum headers.
              </p>
              <div className="grid gap-2 md:grid-cols-2">
                <Input type="datetime-local" value={auditSince} onChange={(event) => setAuditSince(event.target.value)} />
                <Input type="datetime-local" value={auditUntil} onChange={(event) => setAuditUntil(event.target.value)} />
              </div>
              <Button
                variant="outline"
                disabled={auditExport.isPending}
                onClick={async () => {
                  try {
                    const result = await auditExport.mutateAsync({
                      since: auditSince ? new Date(auditSince).toISOString() : undefined,
                      until: auditUntil ? new Date(auditUntil).toISOString() : undefined,
                    });
                    const url = URL.createObjectURL(result.blob);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = `audit-export-${orgId}.ndjson`;
                    document.body.appendChild(link);
                    link.click();
                    link.remove();
                    URL.revokeObjectURL(url);
                    toast.toast({
                      title: "Audit export downloaded",
                      description: `${result.eventCount} events exported${result.checksum ? ` (sha256: ${result.checksum.slice(0, 12)}...)` : ""}.`,
                      variant: "success",
                    });
                  } catch (err) {
                    toast.toast({ title: err instanceof Error ? err.message : "Audit export failed", variant: "danger" });
                  }
                }}
              >
                Download audit NDJSON
              </Button>
            </div>

            <div className="rounded-[22px] border border-danger/30 bg-danger/5 p-4 space-y-3">
              <p className="text-sm font-medium text-danger">PII key rotation</p>
              <p className="text-xs text-muted-foreground">
                Re-encrypts org-scoped sensitive values with the active key set and writes a security audit event.
              </p>
              <Button
                variant="destructive"
                disabled={rotateOrgPii.isPending}
                onClick={async () => {
                  try {
                    const result = await rotateOrgPii.mutateAsync();
                    toast.toast({
                      title: "PII rotation completed",
                      description: `users: ${result.updated_users}, org settings: ${result.updated_org_settings}, at: ${result.rotated_at}`,
                      variant: "warning",
                    });
                  } catch (err) {
                    toast.toast({ title: err instanceof Error ? err.message : "PII rotation failed", variant: "danger" });
                  }
                }}
              >
                Rotate organization PII
              </Button>
            </div>
            <div className="xl:col-span-2 rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-3">
              <p className="text-sm font-medium">Deletion request lifecycle</p>
              <p className="text-xs text-muted-foreground">
                Track organization deletion workflow state and purge completion timestamps.
              </p>
              {(deletionRequests.data?.items.length ?? 0) === 0 ? (
                <p className="text-sm text-muted-foreground">No deletion requests for this organization.</p>
              ) : (
                <div className="space-y-2">
                  {(deletionRequests.data?.items ?? []).map((item) => (
                    <div key={item.id} className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-medium">{item.scope} request</p>
                        <Badge variant={item.status === "PROCESSED" ? "success" : item.status === "PENDING" ? "warning" : "secondary"}>
                          {item.status}
                        </Badge>
                      </div>
                      <p className="mt-2 text-xs text-muted-foreground">
                        delete_after {formatDate(item.delete_after)} | processed_at {item.processed_at ? formatDate(item.processed_at) : "-"}
                      </p>
                      {item.reason ? <p className="mt-1 text-xs text-muted-foreground">reason: {item.reason}</p> : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ) : null}

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

      {isOwner(role) ? (
        <Card>
          <CardHeader>
            <CardTitle>Runtime SLOs</CardTitle>
            <CardDescription>
              Rolling endpoint p95 and 5xx error-rate window ({runtimeSlos.data?.window_seconds ?? 0}s).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {(runtimeSlos.data?.endpoints.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">No runtime samples yet for this window.</p>
            ) : (
              runtimeSlos.data?.endpoints.map((row) => (
                <div key={row.endpoint} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="font-medium">{row.endpoint}</p>
                    <Badge variant={row.breach ? "destructive" : "success"}>{row.breach ? "breach" : "ok"}</Badge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    requests {row.requests} | p95 {row.p95_ms}ms (threshold {runtimeSlos.data?.p95_threshold_ms}ms) | 5xx{" "}
                    {row.error_rate_pct}% (threshold {runtimeSlos.data?.error_rate_threshold_pct}%)
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      ) : null}

      {isOwner(role) ? (
        <Card>
          <CardHeader>
            <CardTitle>Operational diagnostics</CardTitle>
            <CardDescription>DLQ replay controls, queue lag, and worker-health indicators in one panel.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-5">
              <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                <p className="text-xs uppercase text-muted-foreground">Worker health</p>
                <p className={`mt-2 text-sm font-semibold ${runtimeMetrics.data?.worker_health === "degraded" ? "text-danger" : "text-emerald-600"}`}>
                  {runtimeMetrics.data?.worker_health ?? "-"}
                </p>
              </div>
              <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                <p className="text-xs uppercase text-muted-foreground">Queue lag</p>
                <p className="mt-2 text-sm font-semibold">{runtimeMetrics.data?.queue_lag_seconds ?? 0}s</p>
              </div>
              <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                <p className="text-xs uppercase text-muted-foreground">Dead-letter open</p>
                <p className="mt-2 text-sm font-semibold">{runtimeMetrics.data?.dead_letter_open ?? 0}</p>
              </div>
              <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                <p className="text-xs uppercase text-muted-foreground">DB active</p>
                <p className="mt-2 text-sm font-semibold">{runtimeMetrics.data?.db_active_connections ?? 0}</p>
              </div>
              <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                <p className="text-xs uppercase text-muted-foreground">Lockout escalations</p>
                <p className="mt-2 text-sm font-semibold">{runtimeMetrics.data?.auth_lockout_escalations_total ?? 0}</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="w-40">
                <Select
                  value={deadLetterStatus}
                  onValueChange={(value) => {
                    setDeadLetterStatus(value);
                    setDeadLetterPage(1);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All statuses</SelectItem>
                    <SelectItem value="OPEN">Open</SelectItem>
                    <SelectItem value="REPLAYED">Replayed</SelectItem>
                    <SelectItem value="DISMISSED">Dismissed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {Object.entries(deadLetter.data?.counts_by_status ?? {}).map(([key, value]) => (
                <Badge key={key} variant={key === "OPEN" ? "destructive" : key === "REPLAYED" ? "success" : "secondary"}>
                  {key}: {value}
                </Badge>
              ))}
            </div>

            {(deadLetter.data?.items.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">No dead-letter entries for this filter.</p>
            ) : (
              deadLetter.data?.items.map((item) => (
                <div key={item.id} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{item.source_type}: {item.source_name}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Attempts {item.attempts} | Last failed {formatDate(item.last_failed_at)}
                      </p>
                    </div>
                    <Badge variant={item.status === "OPEN" ? "destructive" : item.status === "REPLAYED" ? "success" : "secondary"}>
                      {item.status}
                    </Badge>
                  </div>
                  {item.last_error ? <p className="mt-3 text-xs text-danger">{item.last_error}</p> : null}
                  <pre className="mt-3 overflow-auto rounded-[18px] border border-border/60 bg-background/65 p-3 text-xs">
                    {JSON.stringify(item.payload ?? {}, null, 2)}
                  </pre>
                  {item.status === "OPEN" ? (
                    <div className="mt-3 flex flex-wrap justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={dismissDeadLetter.isPending}
                        onClick={async () => {
                          await dismissDeadLetter.mutateAsync({ eventId: item.id, reason: "operator-dismissed" });
                          toast.toast({ title: "Dead-letter dismissed", description: item.id, variant: "warning" });
                        }}
                      >
                        Dismiss
                      </Button>
                      <Button
                        size="sm"
                        disabled={replayDeadLetter.isPending}
                        onClick={async () => {
                          const result = await replayDeadLetter.mutateAsync(item.id);
                          toast.toast({ title: "Replay dispatched", description: result.replay_ref ?? item.id, variant: "success" });
                        }}
                      >
                        Replay
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))
            )}

            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">{deadLetter.data?.total ?? 0} total dead-letter rows</p>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" disabled={deadLetterPage <= 1} onClick={() => setDeadLetterPage((value) => value - 1)}>
                  Prev
                </Button>
                <span className="text-sm">Page {deadLetterPage}</span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={Boolean(deadLetter.data && deadLetterPage * deadLetter.data.page_size >= deadLetter.data.total)}
                  onClick={() => setDeadLetterPage((value) => value + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
