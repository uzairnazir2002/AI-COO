"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useToast } from "@/components/common/use-toast";
import { InlineErrorBanner } from "@/components/states/inline-error-banner";
import { RetryCard } from "@/components/states/retry-card";
import { SkeletonPanel } from "@/components/states/skeleton-panel";
import { SuccessStateCard } from "@/components/states/success-state-card";
import { AlertsWorkspaceContainer } from "@/features/alerts/containers/alerts-workspace-container";
import { useAcknowledgeAlert, useAlertHistory, useAlerts, useAssignAlert, useDismissAlert } from "@/features/alerts/hooks";
import { useOrgMembers } from "@/features/settings/hooks";
import { alertImpactValue } from "@/lib/utils/chart";
import { useAppStore } from "@/store/appStore";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) return error.message;
  return "Request failed. Please try again.";
}

export default function AlertsPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"open" | "dismissed">("open");
  const [kind, setKind] = useState("ALL");
  const [assigneeFilter, setAssigneeFilter] = useState("ALL");
  const [assigneeSelection, setAssigneeSelection] = useState("");
  const [activeAlertId, setActiveAlertId] = useState<string | null>(null);
  const [lastSuccess, setLastSuccess] = useState("");
  const userId = useAppStore((s) => s.user?.id ?? null);
  const alerts = useAlerts(status, assigneeFilter !== "ALL" && assigneeFilter !== "UNASSIGNED" ? assigneeFilter : undefined);
  const members = useOrgMembers();
  const dismiss = useDismissAlert();
  const assign = useAssignAlert();
  const acknowledge = useAcknowledgeAlert();
  const history = useAlertHistory(activeAlertId);
  const toast = useToast();

  const filtered = useMemo(() => {
    const items = alerts.data?.items ?? [];
    const kindFiltered = kind === "ALL" ? items : items.filter((a) => a.kind === kind);
    if (assigneeFilter === "UNASSIGNED") {
      return kindFiltered.filter((a) => !a.assigned_to_user_id);
    }
    return kindFiltered;
  }, [alerts.data?.items, kind, assigneeFilter]);
  const maxImpact = useMemo(() => filtered.reduce((acc, row) => Math.max(acc, alertImpactValue(row.meta)), 0), [filtered]);
  const activeAlert = filtered.find((row) => row.id === activeAlertId) ?? null;
  const memberEmailById = useMemo(
    () => new Map((members.data ?? []).map((member) => [member.user_id, member.email])),
    [members.data],
  );

  useEffect(() => {
    const nextStatus = searchParams.get("status");
    const nextKind = searchParams.get("kind");
    const nextAssignee = searchParams.get("assignee");
    if (nextStatus === "open" || nextStatus === "dismissed") setStatus(nextStatus);
    if (nextKind) setKind(nextKind);
    if (nextAssignee) setAssigneeFilter(nextAssignee);
  }, [searchParams]);

  useEffect(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("status", status);
    params.set("kind", kind);
    params.set("assignee", assigneeFilter);
    if (params.toString() !== searchParams.toString()) {
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    }
  }, [assigneeFilter, kind, pathname, router, searchParams, status]);

  useEffect(() => {
    if (!activeAlert) return;
    setAssigneeSelection(activeAlert.assigned_to_user_id || "UNASSIGNED_PICK");
  }, [activeAlert]);

  return (
    <div className="space-y-4">
      {alerts.isLoading ? <SkeletonPanel rows={4} /> : null}

      {alerts.error || members.error || history.error ? (
        <div className="space-y-3">
          <InlineErrorBanner
            message={getErrorMessage(alerts.error || members.error || history.error)}
          />
          <RetryCard
            message="Retry loading alert feed, members, and assignment history."
            onRetry={() => {
              void alerts.refetch();
              void members.refetch();
              void history.refetch();
            }}
          />
        </div>
      ) : null}

      {lastSuccess ? <SuccessStateCard title="Alert action completed" description={lastSuccess} /> : null}

      <AlertsWorkspaceContainer
        status={status}
        onStatusChange={setStatus}
        kind={kind}
        onKindChange={setKind}
        assigneeFilter={assigneeFilter}
        onAssigneeFilterChange={setAssigneeFilter}
        members={members.data ?? []}
        filtered={filtered}
        maxImpact={maxImpact}
        onDismiss={async (id) => {
          try {
            await dismiss.mutateAsync(id);
            setLastSuccess("Alert dismissed.");
            toast.toast({ title: "Alert dismissed" });
          } catch (error) {
            toast.toast({ title: "Could not dismiss alert", description: getErrorMessage(error), variant: "danger" });
          }
        }}
        activeAlert={activeAlert}
        onCloseDetail={() => setActiveAlertId(null)}
        userId={userId}
        onAssignToMe={async (id) => {
          if (!userId) return;
          try {
            await assign.mutateAsync({ id, assigneeUserId: userId });
            setLastSuccess("Alert assigned to your user.");
            toast.toast({ title: "Alert assigned to you" });
          } catch (error) {
            toast.toast({ title: "Could not assign alert", description: getErrorMessage(error), variant: "danger" });
          }
        }}
        onUnassign={async (id) => {
          try {
            await assign.mutateAsync({ id, assigneeUserId: null });
            setLastSuccess("Alert unassigned.");
            toast.toast({ title: "Alert unassigned" });
          } catch (error) {
            toast.toast({ title: "Could not unassign alert", description: getErrorMessage(error), variant: "danger" });
          }
        }}
        onAcknowledge={async (id) => {
          try {
            await acknowledge.mutateAsync(id);
            setLastSuccess("Alert acknowledged.");
            toast.toast({ title: "Alert acknowledged" });
          } catch (error) {
            toast.toast({ title: "Could not acknowledge alert", description: getErrorMessage(error), variant: "danger" });
          }
        }}
        assigneeSelection={assigneeSelection}
        onAssigneeSelectionChange={setAssigneeSelection}
        onAssignToMember={async (id, memberId) => {
          try {
            await assign.mutateAsync({ id, assigneeUserId: memberId });
            setLastSuccess("Alert assignment updated.");
            toast.toast({ title: "Alert assignment updated" });
          } catch (error) {
            toast.toast({ title: "Could not update assignee", description: getErrorMessage(error), variant: "danger" });
          }
        }}
        historyItems={history.data?.items ?? []}
        memberEmailById={memberEmailById}
        onOpenAlert={setActiveAlertId}
      />
    </div>
  );
}
