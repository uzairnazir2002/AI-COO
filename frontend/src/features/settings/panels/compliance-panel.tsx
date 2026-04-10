"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { RoleAwareDisabledHint } from "@/components/safety/role-aware-disabled-hint";
import type { Role } from "@/types/domain";

type DeletionItem = {
  status: string;
  delete_after: string;
  processed_at?: string | null;
};

export function CompliancePanel({
  role,
  accountDeleteReason,
  setAccountDeleteReason,
  requestAccountDeletionPending,
  onRequestAccountDeletion,
  latestAccountDeletion,
  orgDeleteReason,
  setOrgDeleteReason,
  confirmPhrase,
  setConfirmPhrase,
  requestOrgDeletionPending,
  onRequestOrgDeletion,
  latestOrgDeletion,
}: {
  role?: Role;
  accountDeleteReason: string;
  setAccountDeleteReason: (value: string) => void;
  requestAccountDeletionPending: boolean;
  onRequestAccountDeletion: () => Promise<void>;
  latestAccountDeletion?: DeletionItem;
  orgDeleteReason: string;
  setOrgDeleteReason: (value: string) => void;
  confirmPhrase: string;
  setConfirmPhrase: (value: string) => void;
  requestOrgDeletionPending: boolean;
  onRequestOrgDeletion: () => Promise<void>;
  latestOrgDeletion?: DeletionItem;
}) {
  const owner = role === "OWNER";

  return (
    <section id="settings-compliance" className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Data & compliance actions</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-3">
            <p className="text-sm font-medium">Account deletion request</p>
            <p className="text-xs text-muted-foreground">
              Creates a scheduled deletion request with a retention window. You can use this for privacy compliance workflows.
            </p>
            <Input
              placeholder="Optional reason for account deletion"
              value={accountDeleteReason}
              onChange={(event) => setAccountDeleteReason(event.target.value)}
            />
            <Button
              variant="outline"
              disabled={requestAccountDeletionPending}
              onClick={() => void onRequestAccountDeletion()}
            >
              Request account deletion
            </Button>
            {latestAccountDeletion ? (
              <div className="rounded-[18px] border border-border/60 bg-background/65 p-3">
                <p className="text-xs uppercase text-muted-foreground">Latest account request</p>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant={latestAccountDeletion.status === "PROCESSED" ? "success" : "warning"}>
                    {latestAccountDeletion.status}
                  </Badge>
                  <p className="text-xs text-muted-foreground">
                    delete_after {latestAccountDeletion.delete_after}
                    {latestAccountDeletion.processed_at ? ` | processed_at ${latestAccountDeletion.processed_at}` : ""}
                  </p>
                </div>
              </div>
            ) : null}
          </div>

          <div className="rounded-[22px] border border-danger/30 bg-danger/5 p-4 space-y-3">
            <p className="text-sm font-medium text-danger">Organization deletion request (Owner only)</p>
            <p className="text-xs text-muted-foreground">
              This schedules full organization deletion. Type <code>DELETE</code> to enable the request action.
            </p>
            {!owner ? <RoleAwareDisabledHint role={role} requiredRole="OWNER" /> : null}
            <Input
              placeholder="Optional reason for organization deletion"
              value={orgDeleteReason}
              onChange={(event) => setOrgDeleteReason(event.target.value)}
              disabled={!owner}
            />
            <Input
              placeholder='Type "DELETE" to confirm'
              value={confirmPhrase}
              onChange={(event) => setConfirmPhrase(event.target.value)}
              disabled={!owner}
            />
            <Button
              variant="destructive"
              disabled={!owner || confirmPhrase !== "DELETE" || requestOrgDeletionPending}
              onClick={() => void onRequestOrgDeletion()}
            >
              Request organization deletion
            </Button>
            {owner && latestOrgDeletion ? (
              <div className="rounded-[18px] border border-danger/20 bg-background/65 p-3">
                <p className="text-xs uppercase text-muted-foreground">Latest org deletion request</p>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant={latestOrgDeletion.status === "PROCESSED" ? "success" : "warning"}>
                    {latestOrgDeletion.status}
                  </Badge>
                  <p className="text-xs text-muted-foreground">
                    delete_after {latestOrgDeletion.delete_after}
                    {latestOrgDeletion.processed_at ? ` | processed_at ${latestOrgDeletion.processed_at}` : ""}
                  </p>
                </div>
              </div>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

