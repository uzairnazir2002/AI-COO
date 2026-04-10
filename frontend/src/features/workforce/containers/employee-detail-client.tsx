"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Edit, Trash2 } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionHeader } from "@/components/common/section-header";
import { PermissionState } from "@/components/states/permission-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { canEdit, isOwner } from "@/lib/auth/rbac";
import { todayISO } from "@/lib/utils/format";
import { useLocations } from "@/features/locations/hooks";
import {
  useDeactivateWorkforceEmployee,
  useUpdateWorkforceEmployee,
  useWorkforceDepartments,
  useWorkforceEmployee,
  useWorkforceEmployees,
  useWorkforceTitles,
} from "@/features/workforce/hooks";
import { EmployeeDialog } from "@/features/workforce/panels/employee-dialog";
import { useAppStore } from "@/store/appStore";

export function EmployeeDetailClient({ employeeId }: { employeeId: string }) {
  const selectedOrg = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId));
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = selectedOrg?.role;

  const employee = useWorkforceEmployee(employeeId);
  const departments = useWorkforceDepartments(true);
  const titles = useWorkforceTitles(true);
  const locations = useLocations({ includeInactive: true });
  const allEmployees = useWorkforceEmployees({ include_inactive: false, limit: 500 });

  const updateEmployee = useUpdateWorkforceEmployee();
  const deactivateEmployee = useDeactivateWorkforceEmployee();
  const [editOpen, setEditOpen] = useState(false);

  const deptIndex = useMemo(() => new Map((departments.data ?? []).map((d) => [d.id, d])), [departments.data]);
  const titleIndex = useMemo(() => new Map((titles.data ?? []).map((t) => [t.id, t])), [titles.data]);
  const locationIndex = useMemo(() => new Map((locations.data ?? []).map((l) => [l.id, l])), [locations.data]);
  const managerIndex = useMemo(() => new Map((allEmployees.data ?? []).map((e) => [e.id, e])), [allEmployees.data]);

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="Employee"
        title="Select an organization to view employees."
        description="Employees are org-scoped. Pick an org in the header."
        actions={[{ label: "Back to workforce", href: "/app/workforce" }]}
      />
    );
  }

  if (employee.error) {
    return (
      <ErrorState
        title="Employee failed to load"
        description={employee.error instanceof Error ? employee.error.message : String(employee.error)}
        onRetry={() => void employee.refetch()}
      />
    );
  }

  if (employee.isLoading || !employee.data) {
    return <Skeleton className="h-80 w-full rounded-[28px]" />;
  }

  const emp = employee.data;
  const dept = emp.department_id ? deptIndex.get(emp.department_id) : null;
  const title = emp.title_id ? titleIndex.get(emp.title_id) : null;
  const location = emp.location_id ? locationIndex.get(emp.location_id) : null;
  const manager = emp.manager_employee_id ? managerIndex.get(emp.manager_employee_id) : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link href="/app/workforce/employees">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
      </div>

      <SectionHeader
        eyebrow="Employee"
        title={`${emp.first_name} ${emp.last_name}`}
        description={emp.employee_code ? `Employee code: ${emp.employee_code}` : "Employee profile"}
        actions={
          canEdit(role) ? (
            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline">
                <Link href={`/app/workforce/attendance?tab=daily&employee_id=${emp.id}&day=${todayISO()}`}>
                  View attendance
                </Link>
              </Button>
              <Button variant="outline" onClick={() => setEditOpen(true)}>
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </Button>
              {isOwner(role) ? (
                <Button
                  variant="outline"
                  onClick={async () => {
                    await deactivateEmployee.mutateAsync(emp.id);
                  }}
                  disabled={deactivateEmployee.isPending}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Deactivate
                </Button>
              ) : null}
            </div>
          ) : (
            <PermissionState message="Read-only access for this organization." />
          )
        }
      />

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Details</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <DetailRow label="Email" value={emp.email ?? "—"} />
            <DetailRow label="Phone" value={emp.phone ?? "—"} />
            <DetailRow label="Department" value={dept?.name ?? "—"} />
            <DetailRow label="Title" value={title?.name ?? "—"} />
            <DetailRow label="Manager" value={manager ? `${manager.first_name} ${manager.last_name}` : "—"} />
            <DetailRow label="Location" value={location?.name ?? "All locations"} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Employment</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <DetailRow label="Status" value={emp.employment_status} />
            <DetailRow label="Type" value={emp.employment_type} />
            <DetailRow label="Start date" value={emp.start_date ?? "—"} />
            <DetailRow label="End date" value={emp.end_date ?? "—"} />
            <DetailRow label="Salary type" value={emp.salary_type} />
            <DetailRow label="Base salary" value={emp.base_salary ?? "—"} />
            <DetailRow label="Hourly rate" value={emp.hourly_rate ?? "—"} />
            {role === "VIEWER" ? (
              <p className="pt-2 text-xs text-muted-foreground">
                Compensation values are hidden for viewers.
              </p>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <EmployeeDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        title="Edit employee"
        submitLabel="Save"
        pending={updateEmployee.isPending}
        initial={emp}
        departments={departments.data ?? []}
        titles={titles.data ?? []}
        locations={locations.data ?? []}
        managerOptions={(allEmployees.data ?? []).filter((e) => e.id !== emp.id)}
        onSubmit={async (payload) => {
          await updateEmployee.mutateAsync({ id: emp.id, ...payload });
          setEditOpen(false);
        }}
      />
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-border/70 bg-card/70 px-4 py-3">
      <p className="text-muted-foreground">{label}</p>
      <p className="min-w-0 truncate font-medium">{value}</p>
    </div>
  );
}

