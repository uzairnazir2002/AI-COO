"use client";

import { useMemo, useState } from "react";

import { InlineValidationHint } from "@/components/safety/inline-validation-hint";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getAlertRecommendations } from "@/features/alerts/services/recommendations";
import type { Alert } from "@/types/domain";

function formatTimelineTimestamp(iso: string) {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.round(diffMs / 60000);
  const abs = date.toLocaleString();
  if (Math.abs(diffMinutes) < 60) {
    const minutes = Math.max(1, Math.abs(diffMinutes));
    return `${minutes}m ${diffMinutes >= 0 ? "ago" : "from now"} (${abs})`;
  }
  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) {
    const hours = Math.max(1, Math.abs(diffHours));
    return `${hours}h ${diffHours >= 0 ? "ago" : "from now"} (${abs})`;
  }
  const diffDays = Math.round(diffHours / 24);
  const days = Math.max(1, Math.abs(diffDays));
  return `${days}d ${diffDays >= 0 ? "ago" : "from now"} (${abs})`;
}

export function AlertActionPanel({
  alert,
  editable,
  userId,
  members,
  assigneeSelection,
  onAssigneeSelectionChange,
  onAssignToMe,
  onUnassign,
  onAcknowledge,
  onDismiss,
  onAssignToMember,
  historyItems,
  memberEmailById,
}: {
  alert: Alert;
  editable: boolean;
  userId: string | null;
  members: Array<{ user_id: string; email: string }>;
  assigneeSelection: string;
  onAssigneeSelectionChange: (value: string) => void;
  onAssignToMe: (id: string) => Promise<void>;
  onUnassign: (id: string) => Promise<void>;
  onAcknowledge: (id: string) => Promise<void>;
  onDismiss: (id: string) => Promise<void>;
  onAssignToMember: (id: string, memberId: string | null) => Promise<void>;
  historyItems: Array<{ id: string; action: string; created_at: string; actor_user_id: string | null }>;
  memberEmailById: Map<string, string>;
}) {
  const [assigneeError, setAssigneeError] = useState<string | null>(null);
  const isAssignedToMe = Boolean(userId && alert.assigned_to_user_id === userId);
  const validMemberIds = useMemo(() => new Set(members.map((member) => member.user_id)), [members]);
  const recommendations = useMemo(() => getAlertRecommendations(alert, isAssignedToMe), [alert, isAssignedToMe]);
  const canMutate = editable;

  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-border/70 bg-card/75 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Actions</p>
        {!canMutate ? (
          <p className="mt-2 text-xs text-muted-foreground">Viewer role detected. You can review alerts but cannot acknowledge, assign, or dismiss.</p>
        ) : null}
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant={isAssignedToMe ? "secondary" : "outline"} disabled={!canMutate} onClick={() => void onAssignToMe(alert.id)}>
            {isAssignedToMe ? "Assigned to you" : "Assign to me"}
          </Button>
          <Button size="sm" variant="outline" disabled={!canMutate} onClick={() => void onAcknowledge(alert.id)}>
            {alert.acknowledged_at ? "Acknowledged" : "Acknowledge"}
          </Button>
          {alert.status === "OPEN" ? (
            <Button size="sm" variant="ghost" disabled={!canMutate} onClick={() => void onDismiss(alert.id)}>
              Dismiss
            </Button>
          ) : null}
          {alert.assigned_to_user_id ? (
            <Button size="sm" variant="ghost" disabled={!canMutate} onClick={() => void onUnassign(alert.id)}>
              Unassign
            </Button>
          ) : null}
        </div>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/75 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Assign member</p>
        <div className="mt-3 flex items-center gap-2">
          <div className="w-full">
            <Select disabled={!canMutate} value={assigneeSelection} onValueChange={onAssigneeSelectionChange}>
              <SelectTrigger><SelectValue placeholder="Assign to member" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="UNASSIGNED_PICK">Unassigned</SelectItem>
                {members.map((member) => (
                  <SelectItem key={member.user_id} value={member.user_id}>{member.email}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <InlineValidationHint message={assigneeError} />
          </div>
          <Button
            size="sm"
            variant="outline"
            disabled={!canMutate}
            onClick={() => {
              const nextAssignee = assigneeSelection === "UNASSIGNED_PICK" ? null : assigneeSelection || null;
              if (nextAssignee && !validMemberIds.has(nextAssignee)) {
                setAssigneeError("Selected assignee is no longer an organization member.");
                return;
              }
              setAssigneeError(null);
              void onAssignToMember(alert.id, nextAssignee);
            }}
          >
            Apply
          </Button>
        </div>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/75 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Recommended next actions</p>
        <div className="mt-3 space-y-2">
          {recommendations.map((item) => (
            <div key={item.id} className="rounded-xl border border-border/60 bg-background/60 px-3 py-2 text-xs">
              <p className="font-medium text-foreground">{item.label}</p>
              <p className="mt-1 text-muted-foreground">{item.description}</p>
              <Button
                className="mt-2"
                size="sm"
                variant="outline"
                onClick={() => {
                  if (item.action === "assign_to_me") {
                    void onAssignToMe(alert.id);
                    return;
                  }
                  if (item.action === "acknowledge") {
                    void onAcknowledge(alert.id);
                    return;
                  }
                  if (item.action === "dismiss") {
                    void onDismiss(alert.id);
                  }
                }}
              >
                Run action
              </Button>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/75 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Assignment timeline</p>
        <div className="mt-3 space-y-2">
          {historyItems.length === 0 ? (
            <p className="text-xs text-muted-foreground">No assignment activity yet.</p>
          ) : (
            historyItems.map((item) => (
              <div key={item.id} className="text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{item.action}</span> by{" "}
                {item.actor_user_id ? (memberEmailById.get(item.actor_user_id) ?? item.actor_user_id) : "system"} ·{" "}
                {formatTimelineTimestamp(item.created_at)}
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
