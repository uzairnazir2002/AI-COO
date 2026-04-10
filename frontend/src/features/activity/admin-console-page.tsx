"use client";

import { useEffect, useMemo, useState } from "react";
import { RefreshCcw } from "lucide-react";
import { useSearchParams } from "next/navigation";

import { AdminStatusPanel } from "@/components/activity/admin-status-panel";
import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { TabNav } from "@/components/layout/tab-nav";
import { InlineErrorBanner } from "@/components/states/inline-error-banner";
import { RetryCard } from "@/components/states/retry-card";
import { SkeletonPanel } from "@/components/states/skeleton-panel";
import { SuccessStateCard } from "@/components/states/success-state-card";
import { Button } from "@/components/ui/button";
import { DeadLetterTabPanel } from "@/features/activity/panels/dead-letter-tab-panel";
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
import { JobsTabPanel } from "@/features/activity/panels/jobs-tab-panel";
import { OutboxTabPanel } from "@/features/activity/panels/outbox-tab-panel";
import { RuntimeTabPanel } from "@/features/activity/panels/runtime-tab-panel";
import { SecurityOpsTabPanel } from "@/features/activity/panels/security-ops-tab-panel";
import { isOwner } from "@/lib/auth/rbac";
import { useAppStore } from "@/store/appStore";

export function AdminConsolePage() {
  const searchParams = useSearchParams();
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((org) => org.org_id === s.selectedOrgId)?.role);
  const ownerOnly = !isOwner(role);
  const [status, setStatus] = useState("ALL");
  const [activeTab, setActiveTab] = useState(() => {
    const requested = searchParams.get("tab");
    if (requested === "jobs" || requested === "outbox" || requested === "runtime" || requested === "dead-letter" || requested === "security") {
      return requested;
    }
    return "jobs";
  });
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
  const [lastSuccess, setLastSuccess] = useState("");
  const tabLoading =
    activeTab === "jobs"
      ? jobs.isLoading
      : activeTab === "outbox"
        ? outbox.isLoading || systemStatus.isLoading
        : activeTab === "runtime"
          ? runtimeSlos.isLoading
          : activeTab === "dead-letter"
            ? deadLetter.isLoading || runtimeMetrics.isLoading
            : activeTab === "security"
              ? deletionRequests.isLoading
              : false;
  const tabError =
    activeTab === "jobs"
      ? (jobs.error as Error | undefined)?.message
      : activeTab === "outbox"
        ? (outbox.error as Error | undefined)?.message || (systemStatus.error as Error | undefined)?.message
        : activeTab === "runtime"
          ? (runtimeSlos.error as Error | undefined)?.message
          : activeTab === "dead-letter"
            ? (deadLetter.error as Error | undefined)?.message || (runtimeMetrics.error as Error | undefined)?.message
            : activeTab === "security"
              ? (deletionRequests.error as Error | undefined)?.message
              : null;

  const activeJobs = useMemo(
    () => jobs.data?.items.filter((item) => ["PENDING", "RUNNING", "RETRYING"].includes(item.status)).length ?? 0,
    [jobs.data?.items],
  );

  useEffect(() => {
    if (ownerOnly && activeTab !== "jobs") {
      setActiveTab("jobs");
    }
  }, [activeTab, ownerOnly]);

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
        title="Admin Console"
        description="Advanced operations, runtime tooling, recovery workflows, and security controls."
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

      <TabNav
        active={activeTab}
        onChange={setActiveTab}
        items={[
          { id: "jobs", label: "Jobs" },
          ...(isOwner(role)
            ? ([
                { id: "outbox", label: "Outbox" },
                { id: "runtime", label: "Runtime / SLO" },
                { id: "dead-letter", label: "Dead-letter" },
                { id: "security", label: "Security Ops" },
              ] as const)
            : ([] as const)),
        ]}
      />

      {!isOwner(role) ? (
        <div className="rounded-[24px] border border-border/70 bg-card/60 p-4 text-sm text-muted-foreground">
          Owner-only admin tooling is hidden for your role. You can still review job history in the Jobs tab.
        </div>
      ) : null}

      <AdminStatusPanel title="Admin status">
        <p>Active jobs: {activeJobs}</p>
        <p>Tab: {activeTab}</p>
        <p>Org scope: {orgId}</p>
      </AdminStatusPanel>

      {tabLoading ? <SkeletonPanel rows={4} /> : null}

      {tabError ? (
        <div className="space-y-3">
          <InlineErrorBanner message={tabError} />
          <RetryCard
            message="Retry loading this activity tab."
            onRetry={() => {
              if (activeTab === "jobs") {
                void jobs.refetch();
                return;
              }
              if (activeTab === "outbox") {
                void outbox.refetch();
                void systemStatus.refetch();
                return;
              }
              if (activeTab === "runtime") {
                void runtimeSlos.refetch();
                return;
              }
              if (activeTab === "dead-letter") {
                void deadLetter.refetch();
                void runtimeMetrics.refetch();
                return;
              }
              if (activeTab === "security") {
                void deletionRequests.refetch();
              }
            }}
          />
        </div>
      ) : null}

      {lastSuccess ? <SuccessStateCard title="Activity action completed" description={lastSuccess} /> : null}

      {activeTab === "jobs" ? (
        <JobsTabPanel
          role={role}
          activeJobs={activeJobs}
          jobsTotal={jobs.data?.total ?? 0}
          status={status}
          setStatus={(value) => {
            setStatus(value);
            setPage(1);
          }}
          taskName={taskName}
          setTaskName={(value) => {
            setTaskName(value);
            setPage(1);
          }}
          jobs={jobs.data?.items ?? []}
          page={page}
          pageSize={jobs.data?.page_size ?? 12}
          onPrevPage={() => setPage((value) => value - 1)}
          onNextPage={() => setPage((value) => value + 1)}
          onRetryJob={async (jobId) => {
            const result = await retryJob.mutateAsync(jobId);
            setLastSuccess("Job re-queued successfully.");
            toast.toast({ title: "Job re-queued", description: result.new_task_id ?? result.status, variant: "success" });
          }}
          onCancelJob={async (jobId) => {
            const result = await cancelJob.mutateAsync(jobId);
            toast.toast({ title: "Job cancelled", description: result.status, variant: "warning" });
          }}
        />
      ) : null}

      {activeTab === "security" ? (
        <SecurityOpsTabPanel
          isOwner={isOwner(role)}
          auditSince={auditSince}
          setAuditSince={setAuditSince}
          auditUntil={auditUntil}
          setAuditUntil={setAuditUntil}
          onDownloadAudit={async () => {
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
          auditExportPending={auditExport.isPending}
          onRotatePii={async () => {
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
          rotatePiiPending={rotateOrgPii.isPending}
          deletionRequests={deletionRequests.data?.items ?? []}
        />
      ) : null}

      {activeTab === "outbox" ? (
        <OutboxTabPanel
          isOwner={isOwner(role)}
          outboxStatus={outboxStatus}
          setOutboxStatus={(value) => {
            setOutboxStatus(value);
            setOutboxPage(1);
          }}
          outboxCountsByStatus={outbox.data?.counts_by_status ?? {}}
          outboxItems={outbox.data?.items ?? []}
          outboxTotal={outbox.data?.total ?? 0}
          outboxPage={outboxPage}
          outboxPageSize={outbox.data?.page_size ?? 8}
          onPrevOutboxPage={() => setOutboxPage((value) => value - 1)}
          onNextOutboxPage={() => setOutboxPage((value) => value + 1)}
          retryOutboxPending={retryOutboxEvent.isPending}
          onRetryOutboxEvent={async (eventId) => {
            await retryOutboxEvent.mutateAsync(eventId);
            setLastSuccess("Outbox event re-queued.");
            toast.toast({ title: "Outbox event re-queued", description: "The worker can pick it up on the next cycle.", variant: "success" });
          }}
          scheduler={systemStatus.data?.scheduler ?? []}
          systemJobs={systemStatus.data?.system_jobs ?? []}
          onResumeSchedule={async (name) => {
            await resumeSchedule.mutateAsync(name);
            toast.toast({ title: "Schedule resumed", description: name, variant: "success" });
          }}
          onPauseSchedule={async (name) => {
            await pauseSchedule.mutateAsync(name);
            toast.toast({ title: "Schedule paused", description: name, variant: "warning" });
          }}
          onRunSchedule={async (name) => {
            const result = await runSchedule.mutateAsync(name);
            setLastSuccess("Schedule dispatched.");
            toast.toast({ title: "Schedule dispatched", description: result.task_id, variant: "success" });
          }}
        />
      ) : null}

      {activeTab === "runtime" ? (
        <RuntimeTabPanel
          isOwner={isOwner(role)}
          windowSeconds={runtimeSlos.data?.window_seconds ?? 0}
          p95ThresholdMs={runtimeSlos.data?.p95_threshold_ms ?? 0}
          errorRateThresholdPct={runtimeSlos.data?.error_rate_threshold_pct ?? 0}
          endpoints={runtimeSlos.data?.endpoints ?? []}
        />
      ) : null}

      {activeTab === "dead-letter" ? (
        <DeadLetterTabPanel
          isOwner={isOwner(role)}
          runtimeMetrics={runtimeMetrics.data}
          deadLetterStatus={deadLetterStatus}
          setDeadLetterStatus={(value) => {
            setDeadLetterStatus(value);
            setDeadLetterPage(1);
          }}
          deadLetterCounts={deadLetter.data?.counts_by_status ?? {}}
          deadLetterItems={deadLetter.data?.items ?? []}
          deadLetterTotal={deadLetter.data?.total ?? 0}
          deadLetterPage={deadLetterPage}
          deadLetterPageSize={deadLetter.data?.page_size ?? 8}
          onPrevDeadLetterPage={() => setDeadLetterPage((value) => value - 1)}
          onNextDeadLetterPage={() => setDeadLetterPage((value) => value + 1)}
          dismissDeadLetterPending={dismissDeadLetter.isPending}
          replayDeadLetterPending={replayDeadLetter.isPending}
          onDismissDeadLetter={async (eventId) => {
            await dismissDeadLetter.mutateAsync({ eventId, reason: "operator-dismissed" });
            toast.toast({ title: "Dead-letter dismissed", description: eventId, variant: "warning" });
          }}
          onReplayDeadLetter={async (eventId) => {
            const result = await replayDeadLetter.mutateAsync(eventId);
            setLastSuccess("Dead-letter replay dispatched.");
            toast.toast({ title: "Replay dispatched", description: result.replay_ref ?? eventId, variant: "success" });
          }}
        />
      ) : null}
    </div>
  );
}
