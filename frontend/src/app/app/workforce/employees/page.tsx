"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Plus, Search } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionHeader } from "@/components/common/section-header";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PermissionState } from "@/components/states/permission-state";
import { canEdit } from "@/lib/auth/rbac";
import { useLocations } from "@/features/locations/hooks";
import {
  useCreateWorkforceEmployee,
  useWorkforceDepartments,
  useWorkforceEmployees,
  useWorkforceTitles,
} from "@/features/workforce/hooks";
import { EmployeeDialog } from "@/features/workforce/panels/employee-dialog";
import { useAppStore } from "@/store/appStore";

export default function WorkforceEmployeesPage() {
  const selectedOrg = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId));
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = selectedOrg?.role;
  const [q, setQ] = useState("");
  const [departmentId, setDepartmentId] = useState<string>("__all__");
  const [titleId, setTitleId] = useState<string>("__all__");
  const [status, setStatus] = useState<string>("__all__");
  const [showCreate, setShowCreate] = useState(false);

  const departments = useWorkforceDepartments(true);
  const titles = useWorkforceTitles(true);
  const locations = useLocations({ includeInactive: true });

  const employees = useWorkforceEmployees({
    q: q.trim() ? q.trim() : undefined,
    department_id: departmentId === "__all__" ? undefined : departmentId,
    title_id: titleId === "__all__" ? undefined : titleId,
    employment_status: status === "__all__" ? undefined : status,
    include_inactive: false,
    limit: 200,
  });

  const createEmployee = useCreateWorkforceEmployee();
  const managerOptions = useMemo(() => employees.data ?? [], [employees.data]);

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="Employees"
        title="Select an organization to view employees."
        description="Employees are org-scoped. Pick an organization from the header, then return here."
        actions={[{ label: "Go to workforce", href: "/app/workforce" }]}
      />
    );
  }

  if (employees.error) {
    return (
      <ErrorState
        title="Employees failed to load"
        description={employees.error instanceof Error ? employees.error.message : String(employees.error)}
        onRetry={() => void employees.refetch()}
      />
    );
  }

  const loading = employees.isLoading || departments.isLoading || titles.isLoading;
  const items = employees.data ?? [];
  const deptIndex = new Map((departments.data ?? []).map((d) => [d.id, d]));
  const titleIndex = new Map((titles.data ?? []).map((t) => [t.id, t]));
  const locationIndex = new Map((locations.data ?? []).map((l) => [l.id, l]));

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Workforce"
        title="Employees"
        description="Directory with org-safe visibility and quick filters."
        actions={
          canEdit(role) ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add employee
            </Button>
          ) : (
            <PermissionState message="You have read-only access. Ask an owner/editor to add or edit employees." />
          )
        }
      />

      <div className="flex flex-col gap-3 rounded-[22px] border border-border/70 bg-card/60 p-4 md:flex-row md:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name, email, or employee code"
            className="h-10 pl-9"
          />
        </div>

        <div className="grid gap-2 md:grid-cols-3 md:gap-3">
          <Select value={departmentId} onValueChange={setDepartmentId}>
            <SelectTrigger className="h-10 w-full md:w-56"><SelectValue placeholder="Department" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All departments</SelectItem>
              {(departments.data ?? []).map((d) => (
                <SelectItem key={d.id} value={d.id}>
                  {d.name}{d.is_active ? "" : " (inactive)"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={titleId} onValueChange={setTitleId}>
            <SelectTrigger className="h-10 w-full md:w-56"><SelectValue placeholder="Title" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All titles</SelectItem>
              {(titles.data ?? []).map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name}{t.is_active ? "" : " (inactive)"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="h-10 w-full md:w-48"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All statuses</SelectItem>
              <SelectItem value="ACTIVE">Active</SelectItem>
              <SelectItem value="ON_LEAVE">On leave</SelectItem>
              <SelectItem value="OFFBOARDED">Offboarded</SelectItem>
              <SelectItem value="TERMINATED">Terminated</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" aria-busy="true" aria-label="Loading employees">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-[22px]" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          eyebrow="Employees"
          title="No employees yet."
          description="Create your first employee to start tracking workforce operations."
          actions={canEdit(role) ? [{ label: "Add employee", onClick: () => setShowCreate(true) }] : []}
        />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.map((emp) => {
            const dept = emp.department_id ? deptIndex.get(emp.department_id) : null;
            const title = emp.title_id ? titleIndex.get(emp.title_id) : null;
            const location = emp.location_id ? locationIndex.get(emp.location_id) : null;
            return (
              <Link
                key={emp.id}
                href={`/app/workforce/employees/${emp.id}`}
                className="rounded-[22px] border border-border/70 bg-card/70 p-4 transition hover:border-primary/30 hover:shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-base font-semibold">
                      {emp.first_name} {emp.last_name}
                    </p>
                    <p className="mt-1 truncate text-sm text-muted-foreground">
                      {emp.employee_code ? `${emp.employee_code} · ` : ""}
                      {emp.email ?? "No email"}
                    </p>
                  </div>
                  <div className="shrink-0 rounded-full border border-border/70 bg-muted/40 px-3 py-1 text-xs">
                    {emp.employment_status}
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <span className="rounded-full border border-border/70 bg-background/40 px-2 py-1">
                    {dept?.name ?? "No department"}
                  </span>
                  <span className="rounded-full border border-border/70 bg-background/40 px-2 py-1">
                    {title?.name ?? "No title"}
                  </span>
                  <span className="rounded-full border border-border/70 bg-background/40 px-2 py-1">
                    {location?.name ?? "All locations"}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      <EmployeeDialog
        open={showCreate}
        onOpenChange={setShowCreate}
        title="Add employee"
        submitLabel="Create"
        pending={createEmployee.isPending}
        departments={departments.data ?? []}
        titles={titles.data ?? []}
        locations={locations.data ?? []}
        managerOptions={managerOptions}
        onSubmit={async (payload) => {
          await createEmployee.mutateAsync(payload);
          setShowCreate(false);
        }}
      />
    </div>
  );
}

