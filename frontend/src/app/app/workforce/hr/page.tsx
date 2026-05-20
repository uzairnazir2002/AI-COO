"use client";

import { useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionHeader } from "@/components/common/section-header";
import { TabNav } from "@/components/layout/tab-nav";
import { PermissionState } from "@/components/states/permission-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/common/use-toast";
import { canEdit } from "@/lib/auth/rbac";
import {
  uploadWorkforceHrDocument,
  useAcknowledgeWorkforcePolicy,
  useCreateWorkforceChecklistItem,
  useCreateWorkforcePolicy,
  useDeactivateWorkforceHrDocument,
  usePublishWorkforcePolicy,
  useSetWorkforceChecklistDone,
  useWorkforceChecklist,
  useWorkforceDocuments,
  useWorkforceEmployees,
  useWorkforcePolicies,
  useWorkforcePolicyAcks,
} from "@/features/workforce/hooks";
import { useAppStore } from "@/store/appStore";

const ALL_EMPLOYEES = "__all__";

export default function WorkforceHrPage() {
  const { toast } = useToast();
  const selectedOrg = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId));
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = selectedOrg?.role;
  const canMutate = canEdit(role);

  const [tab, setTab] = useState("policies");
  const [employeeId, setEmployeeId] = useState<string>(ALL_EMPLOYEES);

  const employees = useWorkforceEmployees({ include_inactive: false, limit: 500 });
  const selectedEmployeeId = employeeId === ALL_EMPLOYEES ? undefined : employeeId;

  const policies = useWorkforcePolicies(false);
  const createPolicy = useCreateWorkforcePolicy();
  const publishPolicy = usePublishWorkforcePolicy();
  const ackPolicy = useAcknowledgeWorkforcePolicy();

  const [policyCode, setPolicyCode] = useState("");
  const [policyTitle, setPolicyTitle] = useState("");
  const [policyBody, setPolicyBody] = useState("");
  const [activePolicyId, setActivePolicyId] = useState<string>("");
  const policyAcks = useWorkforcePolicyAcks(activePolicyId);

  const checklist = useWorkforceChecklist({
    employee_id: selectedEmployeeId,
    kind: tab === "onboarding" ? "ONBOARDING" : tab === "offboarding" ? "OFFBOARDING" : undefined,
    include_done: true,
  });
  const createChecklist = useCreateWorkforceChecklistItem();
  const setDone = useSetWorkforceChecklistDone();

  const [taskTitle, setTaskTitle] = useState("");
  const [taskDue, setTaskDue] = useState("");

  const documents = useWorkforceDocuments({ employee_id: selectedEmployeeId });
  const deactivateDoc = useDeactivateWorkforceHrDocument();
  const [uploading, setUploading] = useState(false);

  const employeeIndex = useMemo(() => new Map((employees.data ?? []).map((e) => [e.id, e])), [employees.data]);

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="HR Admin"
        title="Select an organization to manage HR workflows."
        description="HR workflows are org-scoped. Choose an organization from the header to continue."
        actions={[{ label: "Back to workforce", href: "/app/workforce" }]}
      />
    );
  }

  const topError =
    (employees.error as Error | undefined)?.message ||
    (policies.error as Error | undefined)?.message ||
    (checklist.error as Error | undefined)?.message ||
    (documents.error as Error | undefined)?.message ||
    (policyAcks.error as Error | undefined)?.message;
  if (topError) {
    return (
      <ErrorState
        title="HR admin failed to load"
        description={topError}
        onRetry={() => {
          void employees.refetch();
          void policies.refetch();
          void checklist.refetch();
          void documents.refetch();
          void policyAcks.refetch();
        }}
      />
    );
  }

  const loading = employees.isLoading || policies.isLoading;

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Workforce"
        title="HR Admin"
        description="Onboarding/offboarding tasks, policies, acknowledgements, and employee documents."
        actions={!canMutate ? <PermissionState message="Read-only access. Owners and editors can manage HR workflows." /> : undefined}
      />

      <div className="flex flex-col gap-3 rounded-[22px] border border-border/70 bg-card/60 p-4 md:flex-row md:items-center md:justify-between">
        <div className="grid gap-1">
          <p className="text-sm font-medium">Employee scope</p>
          <div className="w-full sm:w-[320px] max-w-full">
            <Select value={employeeId} onValueChange={setEmployeeId}>
              <SelectTrigger className="h-10"><SelectValue placeholder="All employees" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_EMPLOYEES}>All employees</SelectItem>
                {(employees.data ?? []).map((e) => (
                  <SelectItem key={e.id} value={e.id}>
                    {e.first_name} {e.last_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <TabNav
        active={tab}
        onChange={setTab}
        items={[
          { id: "policies", label: "Policies" },
          { id: "onboarding", label: "Onboarding" },
          { id: "offboarding", label: "Offboarding" },
          { id: "documents", label: "Documents" },
        ]}
        ariaLabel="HR admin sections"
      />

      {tab === "policies" ? (
        <div className="grid gap-4 xl:grid-cols-[1fr_420px]">
          <Card>
            <CardHeader><CardTitle>Policies</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {loading ? <Skeleton className="h-28 w-full rounded-[22px]" /> : null}
              {(policies.data ?? []).length === 0 && !loading ? (
                <p className="text-sm text-muted-foreground">No policies yet.</p>
              ) : (
                <div className="space-y-2">
                  {(policies.data ?? []).map((p) => (
                    <div key={p.id} className="rounded-[22px] border border-border/70 bg-card/70 p-4 space-y-2">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate font-semibold">{p.title}</p>
                          <p className="text-xs text-muted-foreground">Code {p.code} · v{p.version} · {p.published_at ? "Published" : "Draft"}</p>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline" onClick={() => setActivePolicyId(p.id)}>
                            View acks
                          </Button>
                          {canMutate && !p.published_at ? (
                            <Button
                              size="sm"
                              onClick={async () => {
                                try {
                                  await publishPolicy.mutateAsync(p.id);
                                  toast({ title: "Policy published", variant: "success" });
                                } catch (err) {
                                  toast({ title: err instanceof Error ? err.message : "Publish failed", variant: "danger" });
                                }
                              }}
                            >
                              Publish
                            </Button>
                          ) : null}
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-3 whitespace-pre-wrap">{p.body}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card>
              <CardHeader><CardTitle>Create policy</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <Input placeholder="Code (e.g. SAFETY)" value={policyCode} onChange={(e) => setPolicyCode(e.target.value)} />
                <Input placeholder="Title" value={policyTitle} onChange={(e) => setPolicyTitle(e.target.value)} />
                <textarea
                  className="min-h-[140px] w-full rounded-[18px] border border-border/70 bg-background/40 p-3 text-sm"
                  placeholder="Policy body"
                  value={policyBody}
                  onChange={(e) => setPolicyBody(e.target.value)}
                />
                <Button
                  disabled={!canMutate || createPolicy.isPending || !policyCode.trim() || !policyTitle.trim() || !policyBody.trim()}
                  onClick={async () => {
                    try {
                      await createPolicy.mutateAsync({ code: policyCode, title: policyTitle, body: policyBody, publish_now: true });
                      setPolicyCode("");
                      setPolicyTitle("");
                      setPolicyBody("");
                      toast({ title: "Policy created", variant: "success" });
                    } catch (err) {
                      toast({ title: err instanceof Error ? err.message : "Create failed", variant: "danger" });
                    }
                  }}
                >
                  Create & publish
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Acknowledgements</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Select a policy from the list, then record acknowledgements for an employee (if scoped).
                </p>
                {!activePolicyId ? (
                  <p className="text-sm text-muted-foreground">No policy selected.</p>
                ) : policyAcks.isLoading ? (
                  <Skeleton className="h-24 w-full rounded-[22px]" />
                ) : (
                  <>
                    {selectedEmployeeId && canMutate ? (
                      <Button
                        variant="outline"
                        disabled={ackPolicy.isPending}
                        onClick={async () => {
                          try {
                            await ackPolicy.mutateAsync({ policy_id: activePolicyId, employee_id: selectedEmployeeId });
                            toast({ title: "Acknowledgement recorded", variant: "success" });
                          } catch (err) {
                            toast({ title: err instanceof Error ? err.message : "Ack failed", variant: "danger" });
                          }
                        }}
                      >
                        Mark selected employee acknowledged
                      </Button>
                    ) : (
                      <PermissionState message="Select an employee and ensure you have editor/owner role to record acknowledgements." />
                    )}
                    <div className="space-y-2">
                      {(policyAcks.data ?? []).slice(0, 12).map((a) => {
                        const emp = employeeIndex.get(a.employee_id);
                        return (
                          <div key={a.id} className="rounded-[18px] border border-border/70 bg-card/60 p-3 text-sm">
                            <p className="font-medium">{emp ? `${emp.first_name} ${emp.last_name}` : a.employee_id}</p>
                            <p className="text-xs text-muted-foreground">Ack at {a.acknowledged_at}</p>
                          </div>
                        );
                      })}
                      {(policyAcks.data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">No acknowledgements yet.</p> : null}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      ) : null}

      {tab === "onboarding" || tab === "offboarding" ? (
        <Card>
          <CardHeader><CardTitle>{tab === "onboarding" ? "Onboarding checklist" : "Offboarding checklist"}</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {!selectedEmployeeId ? (
              <EmptyState
                eyebrow="Checklist"
                title="Select an employee to manage checklist items."
                description="Checklists are tracked per employee."
              />
            ) : (
              <>
                <div className="grid gap-2 md:grid-cols-[1fr_180px_auto]">
                  <Input placeholder="Task title" value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} />
                  <Input type="date" value={taskDue} onChange={(e) => setTaskDue(e.target.value)} />
                  <Button
                    disabled={!canMutate || createChecklist.isPending || !taskTitle.trim()}
                    onClick={async () => {
                      try {
                        await createChecklist.mutateAsync({
                          employee_id: selectedEmployeeId,
                          kind: tab === "onboarding" ? "ONBOARDING" : "OFFBOARDING",
                          title: taskTitle,
                          due_date: taskDue || undefined,
                        });
                        setTaskTitle("");
                        setTaskDue("");
                        toast({ title: "Checklist item created", variant: "success" });
                      } catch (err) {
                        toast({ title: err instanceof Error ? err.message : "Create failed", variant: "danger" });
                      }
                    }}
                  >
                    Add
                  </Button>
                </div>

                {checklist.isLoading ? (
                  <Skeleton className="h-40 w-full rounded-[22px]" />
                ) : (checklist.data ?? []).length === 0 ? (
                  <p className="text-sm text-muted-foreground">No checklist items yet.</p>
                ) : (
                  <div className="space-y-2">
                    {(checklist.data ?? []).map((item) => (
                      <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-[22px] border border-border/70 bg-card/70 p-4">
                        <div className="min-w-0">
                          <p className="truncate font-medium">{item.title}</p>
                          <p className="text-xs text-muted-foreground">
                            {item.due_date ? `Due ${item.due_date} · ` : ""}
                            {item.is_done ? `Done ${item.completed_at ?? ""}` : "Pending"}
                          </p>
                        </div>
                        {canMutate ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={setDone.isPending}
                            onClick={async () => {
                              await setDone.mutateAsync({ item_id: item.id, is_done: !item.is_done });
                            }}
                          >
                            {item.is_done ? "Mark pending" : "Mark done"}
                          </Button>
                        ) : null}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      ) : null}

      {tab === "documents" ? (
        <Card>
          <CardHeader><CardTitle>Documents</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {!selectedEmployeeId ? (
              <EmptyState
                eyebrow="Documents"
                title="Select an employee to view and upload documents."
                description="Documents are stored in MinIO and scoped to the selected employee."
              />
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-3">
                  <Input
                    type="file"
                    disabled={!canMutate || uploading}
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      if (!orgId) return;
                      setUploading(true);
                      try {
                        await uploadWorkforceHrDocument(file, { employee_id: selectedEmployeeId });
                        toast({ title: "Document uploaded", variant: "success" });
                      } catch (err) {
                        toast({ title: err instanceof Error ? err.message : "Upload failed", variant: "danger" });
                      } finally {
                        setUploading(false);
                        e.target.value = "";
                      }
                    }}
                  />
                  {!canMutate ? <PermissionState message="Read-only access. Owners and editors can upload documents." /> : null}
                </div>

                {documents.isLoading ? (
                  <Skeleton className="h-32 w-full rounded-[22px]" />
                ) : (documents.data ?? []).length === 0 ? (
                  <p className="text-sm text-muted-foreground">No documents yet.</p>
                ) : (
                  <div className="space-y-2">
                    {(documents.data ?? []).map((doc) => (
                      <div key={doc.id} className="flex flex-wrap items-center justify-between gap-2 rounded-[22px] border border-border/70 bg-card/70 p-4">
                        <div className="min-w-0">
                          <a className="truncate font-medium underline" href={doc.url} target="_blank" rel="noreferrer">
                            {doc.name}
                          </a>
                          <p className="text-xs text-muted-foreground">{doc.content_type} · {doc.size_bytes} bytes</p>
                        </div>
                        {canMutate ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={deactivateDoc.isPending}
                            onClick={async () => {
                              try {
                                await deactivateDoc.mutateAsync(doc.id);
                                toast({ title: "Document archived", variant: "warning" });
                              } catch (err) {
                                toast({ title: err instanceof Error ? err.message : "Archive failed", variant: "danger" });
                              }
                            }}
                          >
                            Archive
                          </Button>
                        ) : null}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

