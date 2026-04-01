"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatDate } from "@/lib/utils/format";
import type { DeletionRequestItem } from "@/types/domain";

export function SecurityOpsTabPanel({
  isOwner,
  auditSince,
  setAuditSince,
  auditUntil,
  setAuditUntil,
  onDownloadAudit,
  auditExportPending,
  onRotatePii,
  rotatePiiPending,
  deletionRequests,
}: {
  isOwner: boolean;
  auditSince: string;
  setAuditSince: (value: string) => void;
  auditUntil: string;
  setAuditUntil: (value: string) => void;
  onDownloadAudit: () => Promise<void>;
  auditExportPending: boolean;
  onRotatePii: () => Promise<void>;
  rotatePiiPending: boolean;
  deletionRequests: DeletionRequestItem[];
}) {
  if (!isOwner) return null;

  return (
    <section id="activity-security" className="space-y-4">
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
            <Button variant="outline" disabled={auditExportPending} onClick={() => void onDownloadAudit()}>
              Download audit NDJSON
            </Button>
          </div>

          <div className="rounded-[22px] border border-danger/30 bg-danger/5 p-4 space-y-3">
            <p className="text-sm font-medium text-danger">PII key rotation</p>
            <p className="text-xs text-muted-foreground">
              Re-encrypts org-scoped sensitive values with the active key set and writes a security audit event.
            </p>
            <Button variant="destructive" disabled={rotatePiiPending} onClick={() => void onRotatePii()}>
              Rotate organization PII
            </Button>
          </div>

          <div className="xl:col-span-2 rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-3">
            <p className="text-sm font-medium">Deletion request lifecycle</p>
            <p className="text-xs text-muted-foreground">
              Track organization deletion workflow state and purge completion timestamps.
            </p>
            {deletionRequests.length === 0 ? (
              <p className="text-sm text-muted-foreground">No deletion requests for this organization.</p>
            ) : (
              <div className="space-y-2">
                {deletionRequests.map((item) => (
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
    </section>
  );
}

