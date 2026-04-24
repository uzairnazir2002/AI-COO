"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { PermissionState } from "@/components/states/permission-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useLocations } from "@/features/locations/hooks";
import {
  uploadWorkforceAnnouncementAttachment,
  useAcknowledgeWorkforceAnnouncement,
  useArchiveWorkforceAnnouncement,
  useCreateWorkforceAnnouncement,
  usePublishWorkforceAnnouncement,
  useUpdateWorkforceAnnouncement,
  useWorkforceAnnouncementDeliveries,
  useWorkforceAnnouncementDetail,
  useWorkforceAnnouncementTemplates,
  useWorkforceAnnouncements,
  useWorkforceDepartments,
  useWorkforceEmployees,
  useWorkforceTitles,
} from "@/features/workforce/hooks";
import { canEdit } from "@/lib/auth/rbac";
import { useAppStore } from "@/store/appStore";

const AUDIENCE_OPTIONS = [
  { value: "ORG_ALL", label: "Entire organization" },
  { value: "DEPARTMENT", label: "Departments" },
  { value: "LOCATION", label: "Locations" },
  { value: "TITLE", label: "Job titles" },
  { value: "MANAGER_TEAM", label: "Manager teams (direct reports)" },
] as const;

function toggleId(id: string, cur: string[]): string[] {
  return cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id];
}

function parseAttachmentsJson(raw: string): { name: string; url: string }[] | undefined {
  const t = raw.trim();
  if (!t) return undefined;
  let j: unknown;
  try {
    j = JSON.parse(t);
  } catch {
    throw new Error("Attachments must be valid JSON (array of {name, url}).");
  }
  if (!Array.isArray(j)) throw new Error("Attachments JSON must be an array.");
  return j.map((item) => {
    if (!item || typeof item !== "object") throw new Error("Invalid attachment entry.");
    const o = item as Record<string, unknown>;
    if (typeof o.name !== "string" || typeof o.url !== "string") throw new Error("Each attachment needs name and url strings.");
    return { name: o.name.trim(), url: o.url.trim() };
  });
}

function audienceIdsForKind(
  kind: string,
  dept: string[],
  loc: string[],
  title: string[],
  managers: string[],
): string[] | undefined {
  if (kind === "ORG_ALL") return undefined;
  if (kind === "DEPARTMENT") return dept;
  if (kind === "LOCATION") return loc;
  if (kind === "TITLE") return title;
  if (kind === "MANAGER_TEAM") return managers;
  return undefined;
}

export default function WorkforceCommunicationsPage() {
  const { toast } = useToast();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const selectedOrg = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId));
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = selectedOrg?.role;
  const canMutate = canEdit(role);

  const [includeArchived, setIncludeArchived] = useState(false);
  const list = useWorkforceAnnouncements(includeArchived);
  const templatesForCompose = useWorkforceAnnouncementTemplates();
  const departments = useWorkforceDepartments(false);
  const titles = useWorkforceTitles(false);
  const locations = useLocations({ includeInactive: false });
  const employees = useWorkforceEmployees({ limit: 250, include_inactive: false });

  const [composeOpen, setComposeOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [priority, setPriority] = useState("NORMAL");
  const [pinned, setPinned] = useState(false);
  const [ackRequired, setAckRequired] = useState(false);
  const [expiresAt, setExpiresAt] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [audienceKind, setAudienceKind] = useState<string>("ORG_ALL");
  const [selDept, setSelDept] = useState<string[]>([]);
  const [selLoc, setSelLoc] = useState<string[]>([]);
  const [selTitle, setSelTitle] = useState<string[]>([]);
  const [selManagers, setSelManagers] = useState<string[]>([]);
  const [sendEmail, setSendEmail] = useState(false);
  const [attachmentsRaw, setAttachmentsRaw] = useState("");
  const [uploadedAttachments, setUploadedAttachments] = useState<{ name: string; url: string }[]>([]);
  /** When set, new draft is linked to this template id (from template library deep link). */
  const [composeTemplateId, setComposeTemplateId] = useState<string | null>(null);

  const [readId, setReadId] = useState<string | null>(null);
  const [deliveryPage, setDeliveryPage] = useState(1);
  const [deliveryStatus, setDeliveryStatus] = useState<string>("ALL");
  const detail = useWorkforceAnnouncementDetail(readId);
  const deliveries = useWorkforceAnnouncementDeliveries(readId, {
    enabled: Boolean(readId && canMutate && detail.data?.status === "PUBLISHED"),
    page: deliveryPage,
    pageSize: 25,
    status: deliveryStatus,
  });

  useEffect(() => {
    setDeliveryPage(1);
    setDeliveryStatus("ALL");
  }, [readId]);

  useEffect(() => {
    const tid = searchParams.get("applyTemplate");
    if (!tid || !canMutate) return;
    if (templatesForCompose.isLoading || templatesForCompose.isFetching) return;
    if (templatesForCompose.isError) {
      toast({ title: "Could not load templates", variant: "danger" });
      router.replace(pathname);
      return;
    }
    const tpl = (templatesForCompose.data ?? []).find((x) => x.id === tid);
    if (!tpl) {
      toast({ title: "Template not found or no longer available.", variant: "danger" });
      router.replace(pathname);
      return;
    }
    setTitle(tpl.name);
    setBody(tpl.body_template);
    setComposeTemplateId(tpl.id);
    setComposeOpen(true);
    router.replace(pathname);
  }, [
    canMutate,
    pathname,
    router,
    searchParams,
    templatesForCompose.data,
    templatesForCompose.isError,
    templatesForCompose.isFetching,
    templatesForCompose.isLoading,
    toast,
  ]);

  const create = useCreateWorkforceAnnouncement();
  const update = useUpdateWorkforceAnnouncement();
  const publish = usePublishWorkforceAnnouncement();
  const archive = useArchiveWorkforceAnnouncement();
  const acknowledge = useAcknowledgeWorkforceAnnouncement();

  const [draftTitle, setDraftTitle] = useState("");
  const [draftBody, setDraftBody] = useState("");
  const [draftSendEmail, setDraftSendEmail] = useState(false);
  const [draftScheduled, setDraftScheduled] = useState("");
  const [draftAudience, setDraftAudience] = useState("ORG_ALL");
  const [draftSelDept, setDraftSelDept] = useState<string[]>([]);
  const [draftSelLoc, setDraftSelLoc] = useState<string[]>([]);
  const [draftSelTitle, setDraftSelTitle] = useState<string[]>([]);
  const [draftSelManagers, setDraftSelManagers] = useState<string[]>([]);

  useEffect(() => {
    const d = detail.data;
    if (d && d.status === "DRAFT" && canMutate) {
      setDraftTitle(d.title);
      setDraftBody(d.body);
      setDraftSendEmail(d.send_email_on_publish);
      setDraftScheduled(d.scheduled_publish_at ? d.scheduled_publish_at.slice(0, 16) : "");
      setDraftAudience(d.audience_kind || "ORG_ALL");
      setDraftSelDept(d.audience_kind === "DEPARTMENT" ? (d.audience_ids ?? []).filter(Boolean) : []);
      setDraftSelLoc(d.audience_kind === "LOCATION" ? (d.audience_ids ?? []).filter(Boolean) : []);
      setDraftSelTitle(d.audience_kind === "TITLE" ? (d.audience_ids ?? []).filter(Boolean) : []);
      setDraftSelManagers(d.audience_kind === "MANAGER_TEAM" ? (d.audience_ids ?? []).filter(Boolean) : []);
    }
  }, [detail.data, canMutate]);

  const audienceSummary = useMemo(() => {
    const d = detail.data;
    if (!d) return "";
    const k = d.audience_kind || "ORG_ALL";
    const label = AUDIENCE_OPTIONS.find((o) => o.value === k)?.label ?? k;
    if (k === "ORG_ALL") return label;
    const n = d.audience_ids?.length ?? 0;
    return `${label} · ${n} selected`;
  }, [detail.data]);

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="Communications"
        title="Select an organization to view announcements."
        description="Announcements are org-scoped. Choose an organization from the header."
        actions={[{ label: "Back to workforce", href: "/app/workforce" }]}
      />
    );
  }

  if (list.error) {
    return (
      <ErrorState
        title="Communications failed to load"
        description={list.error instanceof Error ? list.error.message : String(list.error)}
        onRetry={() => void list.refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Workforce"
        title="Communications"
        description="Targeted audiences, optional email via the outbox, scheduled publishing (Celery), reusable templates, attachment links, and delivery logs for editors."
        actions={
          canMutate ? (
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" size="sm" asChild>
                <Link href="/app/workforce/communications/templates">Template library</Link>
              </Button>
              <Button
                onClick={() => {
                  setComposeTemplateId(null);
                  setComposeOpen(true);
                }}
              >
                New announcement
              </Button>
            </div>
          ) : (
            <PermissionState message="Read-only access. Owners and editors can publish announcements." />
          )
        }
      />

      {canMutate ? (
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input type="checkbox" checked={includeArchived} onChange={(e) => setIncludeArchived(e.target.checked)} />
            Show archived
          </label>
        </div>
      ) : null}

      {list.isLoading ? (
        <Skeleton className="h-64 w-full rounded-[28px]" />
      ) : (list.data ?? []).length === 0 ? (
        <EmptyState
          eyebrow="Announcements"
          title="No announcements yet"
          description={canMutate ? "Create a draft and publish when ready." : "Your organization has not published any announcements you can see."}
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {(list.data ?? []).map((a) => (
            <Card key={a.id} className={a.pinned ? "ring-1 ring-primary/25" : ""}>
              <CardHeader className="space-y-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <CardTitle className="text-base leading-snug">{a.title}</CardTitle>
                  <div className="flex flex-wrap gap-1">
                    {a.pinned ? <Badge variant="secondary">Pinned</Badge> : null}
                    <Badge variant={a.status === "PUBLISHED" ? "success" : a.status === "DRAFT" ? "outline" : "warning"}>
                      {a.status}
                    </Badge>
                    {a.priority === "HIGH" ? <Badge variant="destructive">High</Badge> : null}
                    {a.audience_kind && a.audience_kind !== "ORG_ALL" ? <Badge variant="outline">Targeted</Badge> : null}
                    {a.send_email_on_publish ? <Badge variant="outline">Email</Badge> : null}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  {a.published_at ? `Published ${a.published_at.slice(0, 10)}` : "Draft"}
                  {a.scheduled_publish_at ? ` · Scheduled ${a.scheduled_publish_at.slice(0, 16).replace("T", " ")}` : ""}
                  {a.expires_at ? ` · Expires ${a.expires_at}` : ""}
                </p>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
                <Button variant="outline" size="sm" onClick={() => setReadId(a.id)}>
                  {a.status === "DRAFT" && canMutate ? "Open / edit" : "Open"}
                </Button>
                {canMutate && a.status === "DRAFT" ? (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      disabled={publish.isPending}
                      onClick={async () => {
                        try {
                          await publish.mutateAsync(a.id);
                          toast({ title: "Published", variant: "success" });
                        } catch (err) {
                          toast({ title: err instanceof Error ? err.message : "Publish failed", variant: "danger" });
                        }
                      }}
                    >
                      Publish
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={archive.isPending}
                      onClick={async () => {
                        try {
                          await archive.mutateAsync(a.id);
                          toast({ title: "Archived", variant: "success" });
                        } catch (err) {
                          toast({ title: err instanceof Error ? err.message : "Archive failed", variant: "danger" });
                        }
                      }}
                    >
                      Archive
                    </Button>
                  </div>
                ) : null}
                {canMutate && a.status === "PUBLISHED" ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={archive.isPending}
                    onClick={async () => {
                      try {
                        await archive.mutateAsync(a.id);
                        toast({ title: "Archived", variant: "success" });
                      } catch (err) {
                        toast({ title: err instanceof Error ? err.message : "Archive failed", variant: "danger" });
                      }
                    }}
                  >
                    Archive
                  </Button>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog
        open={composeOpen}
        onOpenChange={(open) => {
          setComposeOpen(open);
          if (!open) setComposeTemplateId(null);
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>New announcement</DialogTitle>
          </DialogHeader>
          <form
            className="grid gap-3"
            onSubmit={async (e) => {
              e.preventDefault();
              let parsedExtra: { name: string; url: string }[] = [];
              try {
                if (attachmentsRaw.trim()) {
                  parsedExtra = parseAttachmentsJson(attachmentsRaw) ?? [];
                }
              } catch (err) {
                toast({ title: err instanceof Error ? err.message : "Invalid attachments", variant: "danger" });
                return;
              }
              const merged = [...uploadedAttachments, ...parsedExtra];
              const attachments = merged.length ? merged : undefined;
              const ids = audienceIdsForKind(audienceKind, selDept, selLoc, selTitle, selManagers);
              if (audienceKind !== "ORG_ALL" && (!ids || ids.length === 0)) {
                toast({ title: "Select at least one target for this audience type.", variant: "danger" });
                return;
              }
              try {
                await create.mutateAsync({
                  title: title.trim(),
                  body: body.trim(),
                  priority,
                  pinned,
                  acknowledgement_required: ackRequired,
                  expires_at: expiresAt.trim() || null,
                  scheduled_publish_at: scheduledAt.trim() ? new Date(scheduledAt).toISOString() : null,
                  audience_kind: audienceKind,
                  audience_ids: ids,
                  attachments,
                  send_email_on_publish: sendEmail,
                  template_id: composeTemplateId,
                });
                setTitle("");
                setBody("");
                setPriority("NORMAL");
                setPinned(false);
                setAckRequired(false);
                setExpiresAt("");
                setScheduledAt("");
                setAudienceKind("ORG_ALL");
                setSelDept([]);
                setSelLoc([]);
                setSelTitle([]);
                setSelManagers([]);
                setSendEmail(false);
                setAttachmentsRaw("");
                setUploadedAttachments([]);
                setComposeTemplateId(null);
                setComposeOpen(false);
                toast({ title: "Draft saved", variant: "success" });
              } catch (err) {
                toast({ title: err instanceof Error ? err.message : "Create failed", variant: "danger" });
              }
            }}
          >
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" required />
            <textarea
              className="min-h-[120px] w-full rounded-xl border border-input bg-card/80 px-3 py-2 text-sm"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Message"
              required
            />
            <div className="grid gap-2">
              <span className="text-sm font-medium">Audience</span>
              <Select value={audienceKind} onValueChange={setAudienceKind}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AUDIENCE_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>
                      {o.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {audienceKind === "DEPARTMENT" ? (
              <div className="max-h-36 space-y-1 overflow-y-auto rounded-xl border border-border/60 p-2 text-sm">
                {(departments.data ?? []).map((d) => (
                  <label key={d.id} className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selDept.includes(d.id)}
                      onChange={() => setSelDept((s) => toggleId(d.id, s))}
                    />
                    {d.name}
                  </label>
                ))}
              </div>
            ) : null}
            {audienceKind === "LOCATION" ? (
              <div className="max-h-36 space-y-1 overflow-y-auto rounded-xl border border-border/60 p-2 text-sm">
                {(locations.data ?? []).map((loc) => (
                  <label key={loc.id} className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selLoc.includes(loc.id)}
                      onChange={() => setSelLoc((s) => toggleId(loc.id, s))}
                    />
                    {loc.name}
                  </label>
                ))}
              </div>
            ) : null}
            {audienceKind === "TITLE" ? (
              <div className="max-h-36 space-y-1 overflow-y-auto rounded-xl border border-border/60 p-2 text-sm">
                {(titles.data ?? []).map((t) => (
                  <label key={t.id} className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selTitle.includes(t.id)}
                      onChange={() => setSelTitle((s) => toggleId(t.id, s))}
                    />
                    {t.name}
                  </label>
                ))}
              </div>
            ) : null}
            {audienceKind === "MANAGER_TEAM" ? (
              <div className="max-h-36 space-y-1 overflow-y-auto rounded-xl border border-border/60 p-2 text-sm">
                <p className="mb-1 text-xs text-muted-foreground">Select managers; their direct reports receive the announcement.</p>
                {(employees.data ?? []).map((emp) => (
                  <label key={emp.id} className="flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selManagers.includes(emp.id)}
                      onChange={() => setSelManagers((s) => toggleId(emp.id, s))}
                    />
                    {emp.first_name} {emp.last_name}
                  </label>
                ))}
              </div>
            ) : null}
            <div className="grid gap-2">
              <span className="text-sm font-medium">Priority</span>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="LOW">Low</SelectItem>
                  <SelectItem value="NORMAL">Normal</SelectItem>
                  <SelectItem value="HIGH">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={pinned} onChange={(e) => setPinned(e.target.checked)} />
              Pin to top
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={ackRequired} onChange={(e) => setAckRequired(e.target.checked)} />
              Require acknowledgement
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={sendEmail} onChange={(e) => setSendEmail(e.target.checked)} />
              Send email on publish (outbox)
            </label>
            <div className="grid gap-2">
              <span className="text-sm font-medium">Schedule publish (optional)</span>
              <p className="text-xs text-muted-foreground">
                Uses your browser&apos;s local timezone; the server stores an instant in UTC. Celery publishes due drafts
                every minute.
              </p>
              <Input type="datetime-local" value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <span className="text-sm font-medium">Expiry (optional)</span>
              <Input type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <span className="text-sm font-medium">Attachments</span>
              <p className="text-xs text-muted-foreground">
                Upload PDF, PNG, JPEG, or plain text (max 10 MB). Files are stored in MinIO; links are time-limited signed
                URLs (about 7 days)—open or paste into JSON for longer-lived public links.
              </p>
              <input
                type="file"
                accept=".pdf,image/png,image/jpeg,image/jpg,text/plain"
                className="text-sm file:mr-2"
                onChange={async (ev) => {
                  const f = ev.target.files?.[0];
                  ev.target.value = "";
                  if (!f || !orgId) return;
                  try {
                    const up = await uploadWorkforceAnnouncementAttachment(orgId, f);
                    setUploadedAttachments((prev) => [...prev, { name: up.name, url: up.url }]);
                    toast({ title: "Uploaded", variant: "success" });
                  } catch (err) {
                    toast({ title: err instanceof Error ? err.message : "Upload failed", variant: "danger" });
                  }
                }}
              />
              {uploadedAttachments.length ? (
                <ul className="space-y-1 text-xs">
                  {uploadedAttachments.map((a) => (
                    <li key={a.url} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/50 px-2 py-1">
                      <a href={a.url} className="text-primary underline" target="_blank" rel="noreferrer">
                        {a.name}
                      </a>
                      <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setUploadedAttachments((p) => p.filter((x) => x.url !== a.url))}>
                        Remove
                      </Button>
                    </li>
                  ))}
                </ul>
              ) : null}
              <span className="text-xs font-medium text-muted-foreground">Or paste JSON (optional)</span>
              <textarea
                className="min-h-[72px] w-full rounded-xl border border-input bg-card/80 px-3 py-2 font-mono text-xs"
                value={attachmentsRaw}
                onChange={(e) => setAttachmentsRaw(e.target.value)}
                placeholder='[{"name":"Handbook","url":"https://..."}]'
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setComposeOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={create.isPending}>
                Save draft
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(readId)} onOpenChange={(o) => !o && setReadId(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          {detail.isLoading ? (
            <Skeleton className="h-40 w-full rounded-[22px]" />
          ) : detail.data ? (
            <>
              <DialogHeader>
                <DialogTitle>{detail.data.title}</DialogTitle>
              </DialogHeader>
              <div className="space-y-3 text-sm">
                <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <span>{audienceSummary}</span>
                  {detail.data.send_email_on_publish ? <span>· Email on publish</span> : null}
                </div>
                <p className="whitespace-pre-wrap text-muted-foreground">{detail.data.body}</p>
                {detail.data.attachments_json?.length ? (
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-foreground">Attachments</p>
                    <ul className="list-inside list-disc text-xs">
                      {detail.data.attachments_json.map((x) => (
                        <li key={x.url}>
                          <a href={x.url} className="text-primary underline" target="_blank" rel="noreferrer">
                            {x.name}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {canMutate && detail.data.status === "DRAFT" ? (
                  <div className="space-y-3 rounded-2xl border border-border/60 p-3">
                    <p className="text-xs font-medium">Edit draft</p>
                    <Input value={draftTitle} onChange={(e) => setDraftTitle(e.target.value)} />
                    <textarea
                      className="min-h-[100px] w-full rounded-xl border border-input bg-card/80 px-3 py-2 text-sm"
                      value={draftBody}
                      onChange={(e) => setDraftBody(e.target.value)}
                    />
                    <label className="flex items-center gap-2 text-xs">
                      <input type="checkbox" checked={draftSendEmail} onChange={(e) => setDraftSendEmail(e.target.checked)} />
                      Send email on publish
                    </label>
                    <div className="grid gap-1">
                      <span className="text-xs font-medium">Schedule</span>
                      <p className="text-[11px] text-muted-foreground">Local time → stored as UTC instant.</p>
                      <Input type="datetime-local" value={draftScheduled} onChange={(e) => setDraftScheduled(e.target.value)} />
                    </div>
                    <div className="grid gap-1">
                      <span className="text-xs font-medium">Audience</span>
                      <Select value={draftAudience} onValueChange={setDraftAudience}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {AUDIENCE_OPTIONS.map((o) => (
                            <SelectItem key={o.value} value={o.value}>
                              {o.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    {draftAudience === "DEPARTMENT" ? (
                      <div className="max-h-28 space-y-1 overflow-y-auto text-xs">
                        {(departments.data ?? []).map((d) => (
                          <label key={d.id} className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={draftSelDept.includes(d.id)}
                              onChange={() => setDraftSelDept((s) => toggleId(d.id, s))}
                            />
                            {d.name}
                          </label>
                        ))}
                      </div>
                    ) : null}
                    {draftAudience === "LOCATION" ? (
                      <div className="max-h-28 space-y-1 overflow-y-auto text-xs">
                        {(locations.data ?? []).map((loc) => (
                          <label key={loc.id} className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={draftSelLoc.includes(loc.id)}
                              onChange={() => setDraftSelLoc((s) => toggleId(loc.id, s))}
                            />
                            {loc.name}
                          </label>
                        ))}
                      </div>
                    ) : null}
                    {draftAudience === "TITLE" ? (
                      <div className="max-h-28 space-y-1 overflow-y-auto text-xs">
                        {(titles.data ?? []).map((t) => (
                          <label key={t.id} className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={draftSelTitle.includes(t.id)}
                              onChange={() => setDraftSelTitle((s) => toggleId(t.id, s))}
                            />
                            {t.name}
                          </label>
                        ))}
                      </div>
                    ) : null}
                    {draftAudience === "MANAGER_TEAM" ? (
                      <div className="max-h-28 space-y-1 overflow-y-auto text-xs">
                        {(employees.data ?? []).map((emp) => (
                          <label key={emp.id} className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={draftSelManagers.includes(emp.id)}
                              onChange={() => setDraftSelManagers((s) => toggleId(emp.id, s))}
                            />
                            {emp.first_name} {emp.last_name}
                          </label>
                        ))}
                      </div>
                    ) : null}
                    <Button
                      size="sm"
                      disabled={update.isPending}
                      onClick={async () => {
                        const ids = audienceIdsForKind(draftAudience, draftSelDept, draftSelLoc, draftSelTitle, draftSelManagers);
                        if (draftAudience !== "ORG_ALL" && (!ids || ids.length === 0)) {
                          toast({ title: "Select audience targets.", variant: "danger" });
                          return;
                        }
                        try {
                          await update.mutateAsync({
                            id: detail.data!.id,
                            title: draftTitle.trim(),
                            body: draftBody.trim(),
                            send_email_on_publish: draftSendEmail,
                            clear_scheduled_publish_at: !draftScheduled.trim(),
                            scheduled_publish_at: draftScheduled.trim() ? new Date(draftScheduled).toISOString() : undefined,
                            audience_kind: draftAudience,
                            audience_ids: draftAudience === "ORG_ALL" ? [] : ids ?? [],
                            audience_ids_clear: draftAudience === "ORG_ALL",
                          });
                          toast({ title: "Draft updated", variant: "success" });
                        } catch (err) {
                          toast({ title: err instanceof Error ? err.message : "Update failed", variant: "danger" });
                        }
                      }}
                    >
                      Save changes
                    </Button>
                  </div>
                ) : null}
                {detail.data.acknowledgement_required ? (
                  detail.data.my_receipt?.acknowledged_at ? (
                    <p className="text-xs text-success">Acknowledged</p>
                  ) : (
                    <Button
                      size="sm"
                      disabled={acknowledge.isPending}
                      onClick={async () => {
                        try {
                          await acknowledge.mutateAsync(detail.data!.id);
                          toast({ title: "Acknowledged", variant: "success" });
                        } catch (err) {
                          toast({ title: err instanceof Error ? err.message : "Failed", variant: "danger" });
                        }
                      }}
                    >
                      Acknowledge
                    </Button>
                  )
                ) : null}
                {canMutate && detail.data.status === "PUBLISHED" ? (
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs font-medium">Email delivery log</p>
                      <div className="flex flex-wrap items-center gap-2">
                        <Select value={deliveryStatus} onValueChange={(v) => { setDeliveryStatus(v); setDeliveryPage(1); }}>
                          <SelectTrigger className="h-8 w-full sm:w-[140px] text-xs">
                            <SelectValue placeholder="Status" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="ALL">All statuses</SelectItem>
                            <SelectItem value="PENDING">PENDING</SelectItem>
                            <SelectItem value="RETRYING">RETRYING</SelectItem>
                            <SelectItem value="SENT">SENT</SelectItem>
                            <SelectItem value="FAILED">FAILED</SelectItem>
                          </SelectContent>
                        </Select>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-8 text-xs"
                          disabled={!deliveries.data?.items.length}
                          onClick={() => {
                            const rows = deliveries.data?.items ?? [];
                            const header = ["recipient_email", "status", "outbox_status", "outbox_attempts", "sent_at", "error"];
                            const esc = (s: string) => `"${s.replace(/"/g, '""')}"`;
                            const lines = [
                              header.join(","),
                              ...rows.map((d) =>
                                [
                                  esc(d.recipient_email),
                                  esc(d.status),
                                  esc(d.outbox_status ?? ""),
                                  String(d.outbox_attempts ?? ""),
                                  esc(d.sent_at ?? ""),
                                  esc((d.outbox_last_error || d.error || "").slice(0, 500)),
                                ].join(","),
                              ),
                            ];
                            void navigator.clipboard.writeText(lines.join("\n"));
                            toast({ title: "Copied CSV to clipboard", variant: "success" });
                          }}
                        >
                          Copy CSV
                        </Button>
                      </div>
                    </div>
                    {deliveries.isLoading ? (
                      <Skeleton className="h-16 w-full" />
                    ) : !deliveries.data?.items.length ? (
                      <p className="text-xs text-muted-foreground">No rows match this filter (or no email was sent).</p>
                    ) : (
                      <>
                        <div className="max-h-52 overflow-auto rounded-xl border border-border/60 text-xs">
                          <table className="w-full border-collapse">
                            <thead>
                              <tr className="border-b border-border/60 text-left">
                                <th className="p-2">To</th>
                                <th className="p-2">Delivery</th>
                                <th className="p-2">Outbox</th>
                                <th className="p-2">Att</th>
                                <th className="p-2">Sent</th>
                              </tr>
                            </thead>
                            <tbody>
                              {deliveries.data.items.map((d) => (
                                <tr key={d.id} className="border-b border-border/40 align-top">
                                  <td className="p-2">{d.recipient_email}</td>
                                  <td className="p-2">{d.status}</td>
                                  <td className="p-2">{d.outbox_status ?? "—"}</td>
                                  <td className="p-2">{d.outbox_attempts ?? "—"}</td>
                                  <td className="p-2">{d.sent_at ? d.sent_at.slice(0, 19).replace("T", " ") : "—"}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        {deliveries.data.items.some((x) => x.error || x.outbox_last_error) ? (
                          <p className="text-[11px] text-muted-foreground">Use Copy CSV for full error text from outbox or delivery rows.</p>
                        ) : null}
                        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                          <span>
                            Page {deliveries.data.page} · {deliveries.data.total} total
                          </span>
                          <div className="flex gap-2">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className="h-7"
                              disabled={deliveryPage <= 1}
                              onClick={() => setDeliveryPage((p) => Math.max(1, p - 1))}
                            >
                              Prev
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className="h-7"
                              disabled={deliveryPage * deliveries.data.page_size >= deliveries.data.total}
                              onClick={() => setDeliveryPage((p) => p + 1)}
                            >
                              Next
                            </Button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                ) : null}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Could not load announcement.</p>
          )}
        </DialogContent>
      </Dialog>

      <div className="flex justify-start">
        <Button asChild variant="outline" size="sm">
          <Link href="/app/workforce">Back to workforce</Link>
        </Button>
      </div>
    </div>
  );
}
