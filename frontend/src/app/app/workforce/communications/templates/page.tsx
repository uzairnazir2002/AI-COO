"use client";

import { useState } from "react";
import Link from "next/link";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { PermissionState } from "@/components/states/permission-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useCreateWorkforceAnnouncementTemplate,
  useUpdateWorkforceAnnouncementTemplate,
  useWorkforceAnnouncementAutomationKeys,
  useWorkforceAnnouncementTemplates,
} from "@/features/workforce/hooks";
import { canEdit } from "@/lib/auth/rbac";
import { useAppStore } from "@/store/appStore";

const PLACEHOLDER_HELP = `Placeholders for title and body (use {name} syntax):
Payroll: {period_start}, {period_end}, {period_label}
Leave: {employee_name}, {start_date}, {end_date}, {days}, {leave_type_name}, {reviewer_note}`;

export default function WorkforceAnnouncementTemplatesPage() {
  const { toast } = useToast();
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const canMutate = canEdit(role);

  const list = useWorkforceAnnouncementTemplates();
  const keys = useWorkforceAnnouncementAutomationKeys();
  const createTpl = useCreateWorkforceAnnouncementTemplate();
  const updateTpl = useUpdateWorkforceAnnouncementTemplate();

  const [name, setName] = useState("");
  const [body, setBody] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [automationKey, setAutomationKey] = useState<string>("");

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editBody, setEditBody] = useState("");
  const [editAutomation, setEditAutomation] = useState<string>("");

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="Templates"
        title="Select an organization"
        description="Templates are org-scoped."
        actions={[{ label: "Back", href: "/app/workforce/communications" }]}
      />
    );
  }

  if (!canMutate) {
    return (
      <div className="space-y-4">
        <SectionHeader eyebrow="Workforce" title="Announcement templates" description="" />
        <PermissionState message="Only owners and editors manage templates." />
        <Button asChild variant="outline" size="sm">
          <Link href="/app/workforce/communications">Back to communications</Link>
        </Button>
      </div>
    );
  }

  if (list.error) {
    return (
      <ErrorState
        title="Failed to load templates"
        description={list.error instanceof Error ? list.error.message : String(list.error)}
        onRetry={() => void list.refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Workforce"
        title="Announcement templates"
        description="Manual apply from here, or attach an automation key so payroll / leave events publish automatically when a matching template exists."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link href="/app/workforce/communications">Back to communications</Link>
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create template</CardTitle>
          <p className="text-sm text-muted-foreground whitespace-pre-line">{PLACEHOLDER_HELP}</p>
        </CardHeader>
        <CardContent>
          <form
            className="grid max-w-xl gap-3"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await createTpl.mutateAsync({
                  name: name.trim(),
                  body_template: body.trim(),
                  code: code.trim() || null,
                  description: description.trim() || null,
                  automation_key: automationKey.trim() || null,
                });
                setName("");
                setBody("");
                setCode("");
                setDescription("");
                setAutomationKey("");
                toast({ title: "Template created", variant: "success" });
              } catch (err) {
                toast({ title: err instanceof Error ? err.message : "Failed", variant: "danger" });
              }
            }}
          >
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Title template (also used as announcement title)" required />
            <textarea
              className="min-h-[140px] w-full rounded-xl border border-input bg-card/80 px-3 py-2 text-sm"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Body template"
              required
            />
            <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="Optional short code (unique per org)" />
            <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional description" />
            <div className="grid gap-2">
              <span className="text-sm font-medium">Automation key (optional)</span>
              <Select value={automationKey || "__none__"} onValueChange={(v) => setAutomationKey(v === "__none__" ? "" : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="None — manual only" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">None (manual only)</SelectItem>
                  {(keys.data?.keys ?? []).map((k) => (
                    <SelectItem key={k} value={k}>
                      {k}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" disabled={createTpl.isPending}>
              Save template
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Saved templates</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {list.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : (list.data ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No templates yet.</p>
          ) : (
            (list.data ?? []).map((t) => (
              <div key={t.id} className="rounded-2xl border border-border/60 p-4 text-sm">
                {editingId === t.id ? (
                  <div className="grid gap-2">
                    <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
                    <textarea
                      className="min-h-[100px] w-full rounded-xl border border-input bg-card/80 px-3 py-2 text-sm"
                      value={editBody}
                      onChange={(e) => setEditBody(e.target.value)}
                    />
                    <div className="grid gap-2">
                      <span className="text-xs font-medium">Automation key</span>
                      <Select value={editAutomation || "__none__"} onValueChange={(v) => setEditAutomation(v === "__none__" ? "" : v)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="__none__">None</SelectItem>
                          {(keys.data?.keys ?? []).map((k) => (
                            <SelectItem key={k} value={k}>
                              {k}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        disabled={updateTpl.isPending}
                        onClick={async () => {
                          try {
                            await updateTpl.mutateAsync({
                              id: t.id,
                              name: editName.trim(),
                              body_template: editBody.trim(),
                              automation_clear: !editAutomation.trim(),
                              automation_key: editAutomation.trim() || null,
                            });
                            setEditingId(null);
                            toast({ title: "Updated", variant: "success" });
                          } catch (err) {
                            toast({ title: err instanceof Error ? err.message : "Failed", variant: "danger" });
                          }
                        }}
                      >
                        Save
                      </Button>
                      <Button type="button" size="sm" variant="outline" onClick={() => setEditingId(null)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-medium">{t.name}</p>
                        {t.code ? <p className="text-xs text-muted-foreground">Code: {t.code}</p> : null}
                        {t.automation_key ? (
                          <Badge variant="outline" className="mt-1">
                            {t.automation_key}
                          </Badge>
                        ) : null}
                        {!t.is_active ? <Badge variant="warning">Inactive</Badge> : null}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button type="button" size="sm" variant="secondary" asChild>
                          <Link href={`/app/workforce/communications?applyTemplate=${encodeURIComponent(t.id)}`}>
                            Use in announcement
                          </Link>
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setEditingId(t.id);
                            setEditName(t.name);
                            setEditBody(t.body_template);
                            setEditAutomation(t.automation_key ?? "");
                          }}
                        >
                          Edit
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={updateTpl.isPending}
                          onClick={async () => {
                            try {
                              await updateTpl.mutateAsync({ id: t.id, is_active: !t.is_active });
                              toast({ title: t.is_active ? "Deactivated" : "Activated", variant: "success" });
                            } catch (err) {
                              toast({ title: err instanceof Error ? err.message : "Failed", variant: "danger" });
                            }
                          }}
                        >
                          {t.is_active ? "Deactivate" : "Activate"}
                        </Button>
                      </div>
                    </div>
                    <pre className="mt-2 max-h-28 overflow-auto rounded-lg bg-muted/50 p-2 text-xs">{t.body_template}</pre>
                  </>
                )}
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
