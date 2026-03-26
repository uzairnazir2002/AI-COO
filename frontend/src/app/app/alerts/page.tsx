"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BellRing } from "lucide-react";

import { AlertCard } from "@/components/common/alert-card";
import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAcknowledgeAlert, useAlertHistory, useAlerts, useAssignAlert, useDismissAlert } from "@/features/alerts/hooks";
import { useOrgMembers } from "@/features/settings/hooks";
import { alertImpactValue } from "@/lib/utils/chart";
import { useAppStore } from "@/store/appStore";
import type { Alert } from "@/types/domain";

export default function AlertsPage() {
  const [status, setStatus] = useState<"open" | "dismissed">("open");
  const [kind, setKind] = useState("ALL");
  const [assigneeFilter, setAssigneeFilter] = useState("ALL");
  const [assigneeSelection, setAssigneeSelection] = useState("");
  const [activeAlertId, setActiveAlertId] = useState<string | null>(null);
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
    if (!activeAlert) return;
    setAssigneeSelection(activeAlert.assigned_to_user_id || "UNASSIGNED_PICK");
  }, [activeAlert]);

  return (
    <div className="space-y-4">
      <SectionHeader
        title="Alerts"
        description="Open and dismissed signals from anomaly detection, runway pressure, and profit leakage monitoring."
        actions={
          <>
            <div className="w-32">
              <Select value={status} onValueChange={(value) => setStatus(value as "open" | "dismissed")}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="dismissed">Dismissed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-44">
              <Select value={kind} onValueChange={setKind}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All kinds</SelectItem>
                  <SelectItem value="ANOMALY">Anomaly</SelectItem>
                  <SelectItem value="PROFIT_LEAK">Profit leak</SelectItem>
                  <SelectItem value="RUNWAY">Runway</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-48">
              <Select value={assigneeFilter} onValueChange={setAssigneeFilter}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All assignees</SelectItem>
                  <SelectItem value="UNASSIGNED">Unassigned</SelectItem>
                  {(members.data ?? []).map((member) => (
                    <SelectItem key={member.user_id} value={member.user_id}>
                      {member.email}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </>
        }
      />

      {filtered.length === 0 ? (
        <EmptyState
          eyebrow="Quiet board"
          title="No alerts in this view."
          description="Signals appear once enough transaction history exists. Use imports or manual entry to activate monitoring."
          actions={[{ label: "Add transactions", href: "/app/transactions" }]}
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BellRing className="h-4 w-4 text-primary" />
              Alert stream
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {filtered.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                maxImpact={maxImpact}
                assigneeLabel={alert.assigned_to_user_id ? memberEmailById.get(alert.assigned_to_user_id) ?? "Unknown" : null}
                onOpen={setActiveAlertId}
                onDismiss={
                  status === "open"
                    ? async (id) => {
                        await dismiss.mutateAsync(id);
                        toast.toast({ title: "Alert dismissed" });
                      }
                    : undefined
                }
              />
            ))}
          </CardContent>
        </Card>
      )}

      <AnimatePresence>
        {activeAlert ? (
          <>
            <motion.button
              type="button"
              className="fixed inset-0 z-40 bg-background/55 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setActiveAlertId(null)}
              aria-label="Close alert detail"
            />
            <motion.aside
              initial={{ x: 420 }}
              animate={{ x: 0 }}
              exit={{ x: 420 }}
              className="fixed right-0 top-0 z-50 h-full w-full max-w-xl border-l border-border bg-background p-6 shadow-2xl"
            >
              <AlertDetail
                alert={activeAlert}
                userId={userId}
                onClose={() => setActiveAlertId(null)}
                onAssignToMe={async (id) => {
                  if (!userId) return;
                  await assign.mutateAsync({ id, assigneeUserId: userId });
                  toast.toast({ title: "Alert assigned to you" });
                }}
                onUnassign={async (id) => {
                  await assign.mutateAsync({ id, assigneeUserId: null });
                  toast.toast({ title: "Alert unassigned" });
                }}
                onAcknowledge={async (id) => {
                  await acknowledge.mutateAsync(id);
                  toast.toast({ title: "Alert acknowledged" });
                }}
                members={members.data ?? []}
                assigneeSelection={assigneeSelection}
                onAssigneeSelectionChange={setAssigneeSelection}
                onAssignToMember={async (id, memberId) => {
                  await assign.mutateAsync({ id, assigneeUserId: memberId });
                  toast.toast({ title: "Alert assignment updated" });
                }}
                historyItems={history.data?.items ?? []}
                memberEmailById={memberEmailById}
              />
            </motion.aside>
          </>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function AlertDetail({
  alert,
  userId,
  onClose,
  onAssignToMe,
  onUnassign,
  onAcknowledge,
  members,
  assigneeSelection,
  onAssigneeSelectionChange,
  onAssignToMember,
  historyItems,
  memberEmailById,
}: {
  alert: Alert;
  userId: string | null;
  onClose: () => void;
  onAssignToMe: (id: string) => Promise<void>;
  onUnassign: (id: string) => Promise<void>;
  onAcknowledge: (id: string) => Promise<void>;
  members: Array<{ user_id: string; email: string }>;
  assigneeSelection: string;
  onAssigneeSelectionChange: (value: string) => void;
  onAssignToMember: (id: string, memberId: string | null) => Promise<void>;
  historyItems: Array<{ id: string; action: string; created_at: string; actor_user_id: string | null }>;
  memberEmailById: Map<string, string>;
}) {
  const entries = Object.entries(alert.meta || {});
  const isAssignedToMe = Boolean(userId && alert.assigned_to_user_id === userId);
  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Alert detail</p>
          <h2 className="mt-2 text-2xl font-semibold">{alert.title}</h2>
        </div>
        <Button variant="ghost" onClick={onClose}>
          Close
        </Button>
      </div>
      <div className="mt-6 rounded-[24px] border border-border/70 bg-card/75 p-5">
        <p className="text-sm text-muted-foreground">{alert.description}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button size="sm" variant={isAssignedToMe ? "secondary" : "outline"} onClick={() => onAssignToMe(alert.id)}>
            {isAssignedToMe ? "Assigned to you" : "Assign to me"}
          </Button>
          <Button size="sm" variant="outline" onClick={() => onAcknowledge(alert.id)}>
            {alert.acknowledged_at ? "Acknowledged" : "Acknowledge"}
          </Button>
          {alert.assigned_to_user_id ? (
            <Button size="sm" variant="ghost" onClick={() => onUnassign(alert.id)}>
              Unassign
            </Button>
          ) : null}
        </div>
        <div className="mt-4 flex items-center gap-2">
          <div className="w-72">
            <Select value={assigneeSelection} onValueChange={onAssigneeSelectionChange}>
              <SelectTrigger><SelectValue placeholder="Assign to member" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="UNASSIGNED_PICK">Unassigned</SelectItem>
                {members.map((member) => (
                  <SelectItem key={member.user_id} value={member.user_id}>{member.email}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button size="sm" variant="outline" onClick={() => onAssignToMember(alert.id, assigneeSelection === "UNASSIGNED_PICK" ? null : (assigneeSelection || null))}>
            Apply assignee
          </Button>
        </div>
        <div className="mt-4 grid gap-2">
          {entries.length === 0 ? (
            <p className="text-xs text-muted-foreground">No metadata for this alert.</p>
          ) : (
            entries.map(([key, value]) => (
              <div key={key} className="flex items-center justify-between rounded-xl border border-border/60 px-3 py-2 text-xs">
                <span className="uppercase tracking-[0.12em] text-muted-foreground">{key.replace(/_/g, " ")}</span>
                <span className="font-medium">{String(value)}</span>
              </div>
            ))
          )}
        </div>
        <div className="mt-5 rounded-xl border border-border/60 p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Assignment audit trail</p>
          <div className="mt-2 space-y-2">
            {historyItems.length === 0 ? (
              <p className="text-xs text-muted-foreground">No assignment activity yet.</p>
            ) : (
              historyItems.map((item) => (
                <div key={item.id} className="text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">{item.action}</span> by {item.actor_user_id ? (memberEmailById.get(item.actor_user_id) ?? item.actor_user_id) : "system"} at {item.created_at}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </>
  );
}
