"use client";

import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { RightRail } from "@/components/layout/right-rail";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertActionPanel } from "@/features/alerts/panels/alert-action-panel";
import { AlertDetailPanel } from "@/features/alerts/panels/alert-detail-panel";
import { AlertFeedPanel } from "@/features/alerts/panels/alert-feed-panel";
import type { Alert } from "@/types/domain";

export function AlertsWorkspaceContainer({
  status,
  onStatusChange,
  kind,
  onKindChange,
  assigneeFilter,
  onAssigneeFilterChange,
  members,
  filtered,
  maxImpact,
  onDismiss,
  activeAlert,
  onCloseDetail,
  userId,
  onAssignToMe,
  onUnassign,
  onAcknowledge,
  assigneeSelection,
  onAssigneeSelectionChange,
  onAssignToMember,
  historyItems,
  memberEmailById,
  onOpenAlert,
}: {
  status: "open" | "dismissed";
  onStatusChange: (value: "open" | "dismissed") => void;
  kind: string;
  onKindChange: (value: string) => void;
  assigneeFilter: string;
  onAssigneeFilterChange: (value: string) => void;
  members: Array<{ user_id: string; email: string }>;
  filtered: Alert[];
  maxImpact: number;
  onDismiss: (id: string) => Promise<void>;
  activeAlert: Alert | null;
  onCloseDetail: () => void;
  userId: string | null;
  onAssignToMe: (id: string) => Promise<void>;
  onUnassign: (id: string) => Promise<void>;
  onAcknowledge: (id: string) => Promise<void>;
  assigneeSelection: string;
  onAssigneeSelectionChange: (value: string) => void;
  onAssignToMember: (id: string, memberId: string | null) => Promise<void>;
  historyItems: Array<{ id: string; action: string; created_at: string; actor_user_id: string | null }>;
  memberEmailById: Map<string, string>;
  onOpenAlert: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      <SectionHeader
        eyebrow="Intelligence"
        title="Alerts"
        description="Open and dismissed signals from anomaly detection, runway pressure, and profit leakage monitoring."
        scopeChips={[`Status: ${status}`, `Kind: ${kind}`, `Assignee: ${assigneeFilter}`]}
        actions={
          <>
            <div className="w-32">
              <Select value={status} onValueChange={(value) => onStatusChange(value as "open" | "dismissed")}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="dismissed">Dismissed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-44">
              <Select value={kind} onValueChange={onKindChange}>
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
              <Select value={assigneeFilter} onValueChange={onAssigneeFilterChange}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All assignees</SelectItem>
                  <SelectItem value="UNASSIGNED">Unassigned</SelectItem>
                  {members.map((member) => (
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
        <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr_0.9fr]">
          <AlertFeedPanel
            alerts={filtered}
            maxImpact={maxImpact}
            assigneeLabelById={(id) => (id ? memberEmailById.get(id) ?? "Unknown" : null)}
            onOpenAlert={onOpenAlert}
            onDismiss={status === "open" ? onDismiss : undefined}
          />

          {activeAlert ? (
            <AlertDetailPanel alert={activeAlert} />
          ) : (
            <Panel>
              <PanelHeader><h2 className="text-base font-semibold">Alert detail</h2></PanelHeader>
              <PanelBody className="text-sm text-muted-foreground">
                Select an alert from the feed to view impact details, related metrics, and transaction context.
              </PanelBody>
            </Panel>
          )}

          <RightRail sticky>
            {activeAlert ? (
              <AlertActionPanel
                alert={activeAlert}
                userId={userId}
                members={members}
                assigneeSelection={assigneeSelection}
                onAssigneeSelectionChange={onAssigneeSelectionChange}
                onAssignToMe={onAssignToMe}
                onUnassign={onUnassign}
                onAcknowledge={onAcknowledge}
                onDismiss={onDismiss}
                onAssignToMember={onAssignToMember}
                historyItems={historyItems}
                memberEmailById={memberEmailById}
              />
            ) : (
              <Panel>
                <PanelHeader><h2 className="text-base font-semibold">Action panel</h2></PanelHeader>
                <PanelBody className="text-sm text-muted-foreground">
                  Select an alert to assign ownership, acknowledge, dismiss, and view assignment timeline.
                </PanelBody>
              </Panel>
            )}
            <Panel>
              <PanelHeader>
                <h2 className="text-base font-semibold">Workspace summary</h2>
              </PanelHeader>
              <PanelBody className="space-y-2 text-sm text-muted-foreground">
                <p>Total in view: {filtered.length}</p>
                <p>Filter kind: {kind}</p>
                <p>Assignee filter: {assigneeFilter}</p>
                {activeAlert ? (
                  <Button size="sm" variant="ghost" onClick={onCloseDetail}>
                    Clear selection
                  </Button>
                ) : null}
              </PanelBody>
            </Panel>
          </RightRail>
        </div>
      )}
    </div>
  );
}
