"use client";

import { useEffect, useState } from "react";

import { PermissionState } from "@/components/states/permission-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { canEdit } from "@/lib/auth/rbac";
import { useToast } from "@/components/common/use-toast";
import {
  useCreateWorkforceDepartment,
  useCreateWorkforceTitle,
  useDeactivateWorkforceDepartment,
  useDeactivateWorkforceTitle,
  useUpdateWorkforceDepartment,
  useUpdateWorkforceTitle,
  useWorkforceDepartments,
  useWorkforceTitles,
} from "@/features/workforce/hooks";
import type { Role, WorkforceDepartment, WorkforceTitle } from "@/types/domain";

export function WorkforceSettingsPanel({ role }: { role?: Role }) {
  const toast = useToast();
  const canManage = canEdit(role);

  const departments = useWorkforceDepartments(true);
  const titles = useWorkforceTitles(true);

  const createDept = useCreateWorkforceDepartment();
  const updateDept = useUpdateWorkforceDepartment();
  const deactivateDept = useDeactivateWorkforceDepartment();

  const createTitle = useCreateWorkforceTitle();
  const updateTitle = useUpdateWorkforceTitle();
  const deactivateTitle = useDeactivateWorkforceTitle();

  const [deptName, setDeptName] = useState("");
  const [deptCode, setDeptCode] = useState("");
  const [titleName, setTitleName] = useState("");
  const [titleLevel, setTitleLevel] = useState("");
  const [editDept, setEditDept] = useState<WorkforceDepartment | null>(null);
  const [editTitle, setEditTitle] = useState<WorkforceTitle | null>(null);

  const loading = departments.isLoading || titles.isLoading;

  return (
    <section id="settings-workforce" className="space-y-4">
      {!canManage ? (
        <Card>
          <CardHeader><CardTitle>Workforce</CardTitle></CardHeader>
          <CardContent>
            <PermissionState message="Read-only access. Owners and editors can manage departments and titles." />
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Departments</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">Used for directory filtering and future leave/attendance targeting.</p>

            {canManage ? (
              <form
                className="grid gap-2 md:grid-cols-[1fr_160px_auto]"
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    await createDept.mutateAsync({ name: deptName, code: deptCode || null });
                    setDeptName("");
                    setDeptCode("");
                    toast.toast({ title: "Department created", variant: "success" });
                  } catch (err) {
                    toast.toast({ title: err instanceof Error ? err.message : "Create failed", variant: "danger" });
                  }
                }}
              >
                <Input value={deptName} onChange={(e) => setDeptName(e.target.value)} placeholder="Department name" required />
                <Input value={deptCode} onChange={(e) => setDeptCode(e.target.value)} placeholder="Code (optional)" />
                <Button type="submit" disabled={createDept.isPending || deptName.trim().length === 0}>Add</Button>
              </form>
            ) : null}

            {loading ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full rounded-[22px]" />
                ))}
              </div>
            ) : (departments.data ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No departments yet.</p>
            ) : (
              <div className="space-y-2">
                {(departments.data ?? []).map((dept) => (
                  <div
                    key={dept.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-[22px] border border-border/70 bg-card/70 p-4"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">
                        {dept.name} {dept.code ? <span className="text-muted-foreground">({dept.code})</span> : null}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">{dept.is_active ? "Active" : "Inactive"}</p>
                    </div>
                    {canManage ? (
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setEditDept(dept)}
                        >
                          Edit
                        </Button>
                        {dept.is_active ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={deactivateDept.isPending}
                            onClick={async () => {
                              try {
                                await deactivateDept.mutateAsync(dept.id);
                                toast.toast({ title: "Department archived", variant: "warning" });
                              } catch (err) {
                                toast.toast({ title: err instanceof Error ? err.message : "Archive failed", variant: "danger" });
                              }
                            }}
                          >
                            Archive
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={updateDept.isPending}
                            onClick={async () => {
                              try {
                                await updateDept.mutateAsync({ id: dept.id, is_active: true });
                                toast.toast({ title: "Department reactivated", variant: "success" });
                              } catch (err) {
                                toast.toast({ title: err instanceof Error ? err.message : "Update failed", variant: "danger" });
                              }
                            }}
                          >
                            Reactivate
                          </Button>
                        )}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Job titles</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">Used for directory filtering and role targeting for announcements later.</p>

            {canManage ? (
              <form
                className="grid gap-2 md:grid-cols-[1fr_140px_auto]"
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    await createTitle.mutateAsync({
                      name: titleName,
                      level: titleLevel.trim() ? Number(titleLevel) : null,
                    });
                    setTitleName("");
                    setTitleLevel("");
                    toast.toast({ title: "Title created", variant: "success" });
                  } catch (err) {
                    toast.toast({ title: err instanceof Error ? err.message : "Create failed", variant: "danger" });
                  }
                }}
              >
                <Input value={titleName} onChange={(e) => setTitleName(e.target.value)} placeholder="Title name" required />
                <Input value={titleLevel} onChange={(e) => setTitleLevel(e.target.value)} placeholder="Level (optional)" inputMode="numeric" />
                <Button type="submit" disabled={createTitle.isPending || titleName.trim().length === 0}>Add</Button>
              </form>
            ) : null}

            {loading ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full rounded-[22px]" />
                ))}
              </div>
            ) : (titles.data ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No titles yet.</p>
            ) : (
              <div className="space-y-2">
                {(titles.data ?? []).map((t) => (
                  <div
                    key={t.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-[22px] border border-border/70 bg-card/70 p-4"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">
                        {t.name} {t.level !== null ? <span className="text-muted-foreground">(L{t.level})</span> : null}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">{t.is_active ? "Active" : "Inactive"}</p>
                    </div>
                    {canManage ? (
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setEditTitle(t)}
                        >
                          Edit
                        </Button>
                        {t.is_active ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={deactivateTitle.isPending}
                            onClick={async () => {
                              try {
                                await deactivateTitle.mutateAsync(t.id);
                                toast.toast({ title: "Title archived", variant: "warning" });
                              } catch (err) {
                                toast.toast({ title: err instanceof Error ? err.message : "Archive failed", variant: "danger" });
                              }
                            }}
                          >
                            Archive
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={updateTitle.isPending}
                            onClick={async () => {
                              try {
                                await updateTitle.mutateAsync({ id: t.id, is_active: true });
                                toast.toast({ title: "Title reactivated", variant: "success" });
                              } catch (err) {
                                toast.toast({ title: err instanceof Error ? err.message : "Update failed", variant: "danger" });
                              }
                            }}
                          >
                            Reactivate
                          </Button>
                        )}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <EditDepartmentDialog
        open={Boolean(editDept)}
        department={editDept}
        pending={updateDept.isPending}
        onOpenChange={(value) => {
          if (!value) setEditDept(null);
        }}
        onSave={async (payload) => {
          if (!editDept) return;
          await updateDept.mutateAsync({ id: editDept.id, ...payload });
          setEditDept(null);
          toast.toast({ title: "Department updated", variant: "success" });
        }}
      />

      <EditTitleDialog
        open={Boolean(editTitle)}
        titleItem={editTitle}
        pending={updateTitle.isPending}
        onOpenChange={(value) => {
          if (!value) setEditTitle(null);
        }}
        onSave={async (payload) => {
          if (!editTitle) return;
          await updateTitle.mutateAsync({ id: editTitle.id, ...payload });
          setEditTitle(null);
          toast.toast({ title: "Title updated", variant: "success" });
        }}
      />
    </section>
  );
}

function EditDepartmentDialog({
  open,
  onOpenChange,
  pending,
  department,
  onSave,
}: {
  open: boolean;
  onOpenChange: (value: boolean) => void;
  pending: boolean;
  department: WorkforceDepartment | null;
  onSave: (payload: { name?: string | null; code?: string | null }) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  useEffect(() => {
    if (!open) return;
    if (!department) return;
    setName(department.name);
    setCode(department.code ?? "");
  }, [department, open]);

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        onOpenChange(value);
        if (!value) {
          setName("");
          setCode("");
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit department</DialogTitle>
          <DialogDescription>Update the department name/code. Employees referencing it will reflect changes.</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-3"
          onSubmit={async (e) => {
            e.preventDefault();
            await onSave({ name: name.trim() || null, code: code.trim() || null });
          }}
        >
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Department name" required />
          <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="Code (optional)" />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={pending || name.trim().length === 0}>
              Save
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EditTitleDialog({
  open,
  onOpenChange,
  pending,
  titleItem,
  onSave,
}: {
  open: boolean;
  onOpenChange: (value: boolean) => void;
  pending: boolean;
  titleItem: WorkforceTitle | null;
  onSave: (payload: { name?: string | null; level?: number | null }) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [level, setLevel] = useState("");

  useEffect(() => {
    if (!open) return;
    if (!titleItem) return;
    setName(titleItem.name);
    setLevel(titleItem.level === null ? "" : String(titleItem.level));
  }, [open, titleItem]);

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        onOpenChange(value);
        if (!value) {
          setName("");
          setLevel("");
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit title</DialogTitle>
          <DialogDescription>Update the title name/level. Employees referencing it will reflect changes.</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-3"
          onSubmit={async (e) => {
            e.preventDefault();
            await onSave({
              name: name.trim() || null,
              level: level.trim() ? Number(level) : null,
            });
          }}
        >
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Title name" required />
          <Input value={level} onChange={(e) => setLevel(e.target.value)} placeholder="Level (optional)" inputMode="numeric" />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={pending || name.trim().length === 0}>
              Save
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

