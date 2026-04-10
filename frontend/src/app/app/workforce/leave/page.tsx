"use client";

import { useId, useMemo, useState } from "react";
import Link from "next/link";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { useToast } from "@/components/common/use-toast";
import { SectionHeader } from "@/components/common/section-header";
import { TabNav } from "@/components/layout/tab-nav";
import { PermissionState } from "@/components/states/permission-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { canEdit, isOwner } from "@/lib/auth/rbac";
import { formatMonth, startOfMonthISO, todayISO } from "@/lib/utils/format";
import {
  useAllocateWorkforceLeaveBalance,
  useCreateWorkforceLeaveRequest,
  useCreateWorkforceLeaveType,
  useDeactivateWorkforceLeaveType,
  useDecideWorkforceLeaveRequest,
  useWorkforceEmployees,
  useWorkforceLeaveBalances,
  useWorkforceLeaveRequests,
  useWorkforceLeaveTypes,
} from "@/features/workforce/hooks";
import { useAppStore } from "@/store/appStore";
import type { WorkforceLeaveType } from "@/types/domain";

function monthRange(month: string) {
  const [yStr, mStr] = month.split("-");
  const y = Number(yStr);
  const m = Number(mStr);
  const start = new Date(Date.UTC(y, m - 1, 1));
  const end = new Date(Date.UTC(y, m, 0));
  return { from: start.toISOString().slice(0, 10), to: end.toISOString().slice(0, 10), days: end.getUTCDate() };
}

export default function WorkforceLeavePage() {
  const { toast } = useToast();
  const selectedOrg = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId));
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = selectedOrg?.role;
  const canMutate = canEdit(role);
  const owner = isOwner(role);

  const [tab, setTab] = useState("request");
  const [month, setMonth] = useState(() => startOfMonthISO().slice(0, 7));
  const [balanceYear, setBalanceYear] = useState(() => new Date().getFullYear());

  const { from, to, days } = useMemo(() => monthRange(month), [month]);

  const employees = useWorkforceEmployees({ include_inactive: false, limit: 5000 });
  const leaveTypes = useWorkforceLeaveTypes(true);
  const pending = useWorkforceLeaveRequests({ status: "PENDING", limit: 200 });
  const history = useWorkforceLeaveRequests({ from_date: from, to_date: to, limit: 500 });
  const balances = useWorkforceLeaveBalances({ year: balanceYear, limit: 5000 });

  const createRequest = useCreateWorkforceLeaveRequest();
  const decide = useDecideWorkforceLeaveRequest();
  const allocate = useAllocateWorkforceLeaveBalance();
  const createLeaveType = useCreateWorkforceLeaveType();
  const deactivateLeaveType = useDeactivateWorkforceLeaveType();

  const employeeIndex = useMemo(() => new Map((employees.data ?? []).map((e) => [e.id, e])), [employees.data]);
  const leaveTypeIndex = useMemo(() => new Map((leaveTypes.data ?? []).map((t) => [t.id, t])), [leaveTypes.data]);

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="Leave"
        title="Select an organization to manage leave."
        description="Leave is org-scoped. Choose an organization from the header to continue."
        actions={[{ label: "Back to workforce", href: "/app/workforce" }]}
      />
    );
  }

  const topError =
    (employees.error as Error | undefined)?.message ||
    (leaveTypes.error as Error | undefined)?.message ||
    (pending.error as Error | undefined)?.message ||
    (history.error as Error | undefined)?.message ||
    (balances.error as Error | undefined)?.message;
  if (topError) {
    return (
      <ErrorState
        title="Leave failed to load"
        description={topError}
        onRetry={() => {
          void employees.refetch();
          void leaveTypes.refetch();
          void pending.refetch();
          void history.refetch();
          void balances.refetch();
        }}
      />
    );
  }

  const loading = employees.isLoading || leaveTypes.isLoading;

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Workforce"
        title="Leave"
        description="Define leave types, allocate balances, request and approve leave, and view approved time off on the calendar."
        actions={
          !canMutate ? <PermissionState message="Read-only access. Owners and editors can request and approve leave." /> : undefined
        }
      />

      <TabNav
        active={tab}
        onChange={setTab}
        items={[
          { id: "request", label: "Request" },
          { id: "types", label: "Types" },
          { id: "approvals", label: "Approvals" },
          { id: "balances", label: "Balances" },
          { id: "calendar", label: "Calendar" },
        ]}
        ariaLabel="Leave sections"
      />

      {tab === "request" ? (
        loading ? (
          <Skeleton className="h-64 w-full rounded-[28px]" />
        ) : (leaveTypes.data ?? []).filter((t) => t.is_active).length === 0 ? (
          <EmptyState
            eyebrow="Request"
            title="Create a leave type first"
            description="Leave types (for example PTO or sick leave) are required before anyone can submit a request. Owners and editors can add types on the Types tab."
            actions={[
              { label: "Open Types", onClick: () => setTab("types") },
              { label: "Back to workforce", href: "/app/workforce", variant: "outline" },
            ]}
          />
        ) : (
          <RequestLeaveCard
            canMutate={canMutate}
            employees={employees.data ?? []}
            leaveTypes={leaveTypes.data ?? []}
            pending={createRequest.isPending}
            onSubmit={async (payload) => {
              try {
                await createRequest.mutateAsync(payload);
                setTab("approvals");
              } catch (err) {
                toast({
                  title: err instanceof Error ? err.message : "Could not submit leave request",
                  variant: "danger",
                });
              }
            }}
          />
        )
      ) : null}

      {tab === "types" ? (
        leaveTypes.isLoading ? (
          <Skeleton className="h-64 w-full rounded-[28px]" />
        ) : (
          <LeaveTypesPanel
            canMutate={canMutate}
            isOwnerRole={owner}
            types={(leaveTypes.data ?? []) as WorkforceLeaveType[]}
            creating={createLeaveType.isPending}
            deactivating={deactivateLeaveType.isPending}
            onCreate={async (payload) => {
              try {
                await createLeaveType.mutateAsync(payload);
              } catch (err) {
                toast({
                  title: err instanceof Error ? err.message : "Could not create leave type",
                  variant: "danger",
                });
                throw err;
              }
            }}
            onDeactivate={async (id) => {
              try {
                await deactivateLeaveType.mutateAsync(id);
              } catch (err) {
                toast({
                  title: err instanceof Error ? err.message : "Could not deactivate leave type",
                  variant: "danger",
                });
                throw err;
              }
            }}
          />
        )
      ) : null}

      {tab === "approvals" ? (
        pending.isLoading ? (
          <Skeleton className="h-64 w-full rounded-[28px]" />
        ) : (pending.data ?? []).length === 0 ? (
          <EmptyState eyebrow="Approvals" title="No pending leave requests." description="Pending requests will show up here." />
        ) : (
          <div className="grid gap-3">
            {(pending.data ?? []).map((r) => {
              const emp = employeeIndex.get(r.employee_id);
              const lt = leaveTypeIndex.get(r.leave_type_id);
              return (
                <Card key={r.id}>
                  <CardHeader className="flex flex-row items-center justify-between gap-3">
                    <div className="min-w-0">
                      <CardTitle className="truncate">
                        {emp ? `${emp.first_name} ${emp.last_name}` : r.employee_id} · {lt?.name ?? "Leave"}
                      </CardTitle>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {r.start_date} → {r.end_date} · {r.days} day(s)
                      </p>
                      {r.reason ? <p className="mt-2 text-sm text-muted-foreground">{r.reason}</p> : null}
                    </div>
                    {canMutate ? (
                      <div className="flex shrink-0 flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={decide.isPending}
                          onClick={async () => {
                            try {
                              await decide.mutateAsync({ id: r.id, status: "APPROVED" });
                            } catch (err) {
                              toast({
                                title: err instanceof Error ? err.message : "Approve failed",
                                variant: "danger",
                              });
                            }
                          }}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={decide.isPending}
                          onClick={async () => {
                            try {
                              await decide.mutateAsync({ id: r.id, status: "REJECTED" });
                            } catch (err) {
                              toast({
                                title: err instanceof Error ? err.message : "Reject failed",
                                variant: "danger",
                              });
                            }
                          }}
                        >
                          Reject
                        </Button>
                      </div>
                    ) : null}
                  </CardHeader>
                </Card>
              );
            })}
          </div>
        )
      ) : null}

      {tab === "balances" ? (
        balances.isLoading ? (
          <Skeleton className="h-64 w-full rounded-[28px]" />
        ) : (
          <div className="space-y-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="grid gap-2">
                <label htmlFor="leave-balance-year" className="text-sm font-medium">
                  Balance year
                </label>
                <Input
                  id="leave-balance-year"
                  type="number"
                  className="h-10 w-36"
                  min={2000}
                  max={2100}
                  value={balanceYear}
                  onChange={(e) => {
                    const n = Number.parseInt(e.target.value, 10);
                    if (!Number.isFinite(n)) return;
                    setBalanceYear(Math.min(2100, Math.max(2000, n)));
                  }}
                />
              </div>
              <p className="max-w-md pb-2 text-sm text-muted-foreground">
                Allocations and the list below use this year. The calendar month control only affects the Calendar tab.
              </p>
            </div>
            <LeaveBalancesPanel
              canMutate={canMutate}
              year={balanceYear}
              employees={employees.data ?? []}
              leaveTypes={leaveTypes.data ?? []}
              balances={balances.data ?? []}
              allocating={allocate.isPending}
              onAllocate={async (payload) => {
                try {
                  await allocate.mutateAsync(payload);
                } catch (err) {
                  toast({
                    title: err instanceof Error ? err.message : "Allocate failed",
                    variant: "danger",
                  });
                }
              }}
            />
          </div>
        )
      ) : null}

      {tab === "calendar" ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="h-10 w-44" />
              <p className="text-sm text-muted-foreground">Approved leave overlays.</p>
            </div>
            <div className="flex gap-2">
              <Button asChild variant="outline" size="sm">
                <Link href="/app/workforce/attendance">Attendance</Link>
              </Button>
              <p className="text-sm text-muted-foreground">{formatMonth(month)}</p>
            </div>
          </div>

          {history.isLoading ? (
            <Skeleton className="h-64 w-full rounded-[28px]" />
          ) : (
            <LeaveCalendarGrid
              month={month}
              daysInMonth={days}
              requests={(history.data ?? []).filter((r) => r.status === "APPROVED")}
            />
          )}
        </div>
      ) : null}
    </div>
  );
}

function LeaveTypesPanel({
  canMutate,
  isOwnerRole,
  types,
  creating,
  deactivating,
  onCreate,
  onDeactivate,
}: {
  canMutate: boolean;
  isOwnerRole: boolean;
  types: WorkforceLeaveType[];
  creating: boolean;
  deactivating: boolean;
  onCreate: (payload: { name: string; code?: string | null; is_paid: boolean; requires_approval: boolean }) => Promise<void>;
  onDeactivate: (id: string) => Promise<void>;
}) {
  const nameId = useId();
  const codeId = useId();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [payKind, setPayKind] = useState<"paid" | "unpaid">("paid");
  const [approvalKind, setApprovalKind] = useState<"approval" | "auto">("approval");

  return (
    <div className="space-y-6">
      {!canMutate ? <PermissionState message="Read-only access. Owners and editors can manage leave types." /> : null}

      {canMutate ? (
        <Card>
          <CardHeader>
            <CardTitle>Add leave type</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="grid gap-2">
                <label htmlFor={nameId} className="text-sm font-medium">
                  Name
                </label>
                <Input id={nameId} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Annual PTO" />
              </div>
              <div className="grid gap-2">
                <label htmlFor={codeId} className="text-sm font-medium">
                  Code (optional)
                </label>
                <Input
                  id={codeId}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Short code for reports"
                  maxLength={40}
                />
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="grid gap-2">
                <span className="text-sm font-medium">Pay</span>
                <Select value={payKind} onValueChange={(v) => setPayKind(v as "paid" | "unpaid")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="paid">Paid</SelectItem>
                    <SelectItem value="unpaid">Unpaid</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <span className="text-sm font-medium">Approval</span>
                <Select value={approvalKind} onValueChange={(v) => setApprovalKind(v as "approval" | "auto")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="approval">Requires approval</SelectItem>
                    <SelectItem value="auto">Auto-approved</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex justify-end">
              <Button
                disabled={creating || !name.trim()}
                onClick={async () => {
                  try {
                    await onCreate({
                      name: name.trim(),
                      code: code.trim() || null,
                      is_paid: payKind === "paid",
                      requires_approval: approvalKind === "approval",
                    });
                    setName("");
                    setCode("");
                  } catch {
                    /* parent toast */
                  }
                }}
              >
                Create type
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Leave types</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {types.length === 0 ? (
            <p className="text-sm text-muted-foreground">No leave types yet.</p>
          ) : (
            types.map((t) => (
              <div
                key={t.id}
                className="flex flex-col gap-3 rounded-[22px] border border-border/70 bg-card/60 p-4 md:flex-row md:items-center md:justify-between"
              >
                <div className="min-w-0">
                  <p className="font-medium">{t.name}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {t.code ? <Badge variant="secondary">{t.code}</Badge> : null}
                    <Badge variant={t.is_paid ? "success" : "outline"}>{t.is_paid ? "Paid" : "Unpaid"}</Badge>
                    <Badge variant="outline">{t.requires_approval ? "Requires approval" : "Auto-approved"}</Badge>
                    {!t.is_active ? <Badge variant="warning">Inactive</Badge> : null}
                  </div>
                </div>
                {isOwnerRole && t.is_active ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={deactivating}
                    onClick={async () => {
                      try {
                        await onDeactivate(t.id);
                      } catch {
                        /* parent toast */
                      }
                    }}
                  >
                    Deactivate
                  </Button>
                ) : null}
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function RequestLeaveCard({
  canMutate,
  employees,
  leaveTypes,
  pending,
  onSubmit,
}: {
  canMutate: boolean;
  employees: Array<{ id: string; first_name: string; last_name: string }>;
  leaveTypes: Array<{ id: string; name: string; is_active: boolean }>;
  pending: boolean;
  onSubmit: (payload: { employee_id: string; leave_type_id: string; start_date: string; end_date: string; days: string; reason?: string | null }) => Promise<void>;
}) {
  const employeeSelectId = useId();
  const leaveTypeSelectId = useId();
  const startDateId = useId();
  const endDateId = useId();
  const daysId = useId();
  const reasonId = useId();

  const [employeeId, setEmployeeId] = useState(employees[0]?.id ?? "");
  const [leaveTypeId, setLeaveTypeId] = useState(leaveTypes.find((t) => t.is_active)?.id ?? leaveTypes[0]?.id ?? "");
  const [startDate, setStartDate] = useState(todayISO());
  const [endDate, setEndDate] = useState(todayISO());
  const [days, setDays] = useState("1");
  const [reason, setReason] = useState("");

  return (
    <Card>
      <CardHeader><CardTitle>Request leave</CardTitle></CardHeader>
      <CardContent className="grid gap-4">
        {!canMutate ? <PermissionState message="Read-only access. Owners and editors can request leave." /> : null}

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="grid gap-2">
            <label htmlFor={employeeSelectId} className="text-sm font-medium">
              Employee
            </label>
            <Select value={employeeId} onValueChange={setEmployeeId}>
              <SelectTrigger id={employeeSelectId}>
                <SelectValue placeholder="Select employee" />
              </SelectTrigger>
              <SelectContent>
                {employees.map((e) => (
                  <SelectItem key={e.id} value={e.id}>
                    {e.first_name} {e.last_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <label htmlFor={leaveTypeSelectId} className="text-sm font-medium">
              Leave type
            </label>
            <Select value={leaveTypeId} onValueChange={setLeaveTypeId}>
              <SelectTrigger id={leaveTypeSelectId}>
                <SelectValue placeholder="Select leave type" />
              </SelectTrigger>
              <SelectContent>
                {leaveTypes.filter((t) => t.is_active).map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <label htmlFor={startDateId} className="text-sm font-medium">
              Start date
            </label>
            <Input id={startDateId} type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <label htmlFor={endDateId} className="text-sm font-medium">
              End date
            </label>
            <Input id={endDateId} type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="grid gap-2">
            <label htmlFor={daysId} className="text-sm font-medium">
              Days
            </label>
            <Input id={daysId} value={days} onChange={(e) => setDays(e.target.value)} inputMode="decimal" />
            <p className="text-xs text-muted-foreground">For multi-day ranges, set the intended total days (e.g. 2.5).</p>
          </div>
          <div className="grid gap-2">
            <label htmlFor={reasonId} className="text-sm font-medium">
              Reason (optional)
            </label>
            <Input id={reasonId} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Optional note" />
          </div>
        </div>

        <div className="flex justify-end">
          <Button
            disabled={!canMutate || pending || !employeeId || !leaveTypeId || !startDate || !endDate}
            onClick={async () => {
              await onSubmit({
                employee_id: employeeId,
                leave_type_id: leaveTypeId,
                start_date: startDate,
                end_date: endDate,
                days,
                reason: reason || null,
              });
            }}
          >
            Submit request
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function LeaveBalancesPanel({
  canMutate,
  year,
  employees,
  leaveTypes,
  balances,
  allocating,
  onAllocate,
}: {
  canMutate: boolean;
  year: number;
  employees: Array<{ id: string; first_name: string; last_name: string }>;
  leaveTypes: Array<{ id: string; name: string; is_active: boolean }>;
  balances: Array<{ id: string; employee_id: string; leave_type_id: string; allocated_days: string; used_days: string; pending_days: string; year: number }>;
  allocating: boolean;
  onAllocate: (payload: { employee_id: string; leave_type_id: string; year: number; allocated_days: string }) => Promise<void>;
}) {
  const [employeeId, setEmployeeId] = useState(employees[0]?.id ?? "");
  const [leaveTypeId, setLeaveTypeId] = useState(leaveTypes.find((t) => t.is_active)?.id ?? leaveTypes[0]?.id ?? "");
  const [allocatedDays, setAllocatedDays] = useState("10");

  const empIndex = useMemo(() => new Map(employees.map((e) => [e.id, `${e.first_name} ${e.last_name}`])), [employees]);
  const ltIndex = useMemo(() => new Map(leaveTypes.map((t) => [t.id, t.name])), [leaveTypes]);

  return (
    <div className="space-y-4">
      {canMutate ? (
        <Card>
          <CardHeader><CardTitle>Allocate balance</CardTitle></CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-4">
            <Select value={employeeId} onValueChange={setEmployeeId}>
              <SelectTrigger><SelectValue placeholder="Employee" /></SelectTrigger>
              <SelectContent>
                {employees.map((e) => (
                  <SelectItem key={e.id} value={e.id}>
                    {e.first_name} {e.last_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={leaveTypeId} onValueChange={setLeaveTypeId}>
              <SelectTrigger><SelectValue placeholder="Leave type" /></SelectTrigger>
              <SelectContent>
                {leaveTypes.filter((t) => t.is_active).map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input value={allocatedDays} onChange={(e) => setAllocatedDays(e.target.value)} inputMode="decimal" />
            <Button
              disabled={allocating || !employeeId || !leaveTypeId}
              onClick={async () => onAllocate({ employee_id: employeeId, leave_type_id: leaveTypeId, year, allocated_days: allocatedDays })}
            >
              Allocate
            </Button>
          </CardContent>
        </Card>
      ) : (
        <PermissionState message="Read-only access. Owners and editors can allocate balances." />
      )}

      <Card>
        <CardHeader><CardTitle>Balances ({year})</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          {balances.length === 0 ? <p className="text-muted-foreground">No balances yet.</p> : null}
          {balances
            .filter((b) => b.year === year)
            .slice(0, 200)
            .map((b) => (
              <div key={b.id} className="rounded-[22px] border border-border/70 bg-card/60 p-3">
                <p className="font-medium">
                  {empIndex.get(b.employee_id) ?? b.employee_id} · {ltIndex.get(b.leave_type_id) ?? b.leave_type_id}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Allocated {b.allocated_days} · Used {b.used_days} · Pending {b.pending_days}
                </p>
              </div>
            ))}
        </CardContent>
      </Card>
    </div>
  );
}

function LeaveCalendarGrid({
  month,
  daysInMonth,
  requests,
}: {
  month: string;
  daysInMonth: number;
  requests: Array<{ id: string; start_date: string; end_date: string; employee_id: string }>;
}) {
  const dayCounts = useMemo(() => {
    const counts = new Map<string, number>();
    const { from } = monthRange(month);
    const monthStart = new Date(`${from}T00:00:00Z`);
    for (const r of requests) {
      const start = new Date(`${r.start_date}T00:00:00Z`);
      const end = new Date(`${r.end_date}T00:00:00Z`);
      for (let d = new Date(start); d <= end; d.setUTCDate(d.getUTCDate() + 1)) {
        const key = d.toISOString().slice(0, 10);
        if (!key.startsWith(month)) continue;
        counts.set(key, (counts.get(key) ?? 0) + 1);
      }
    }
    // ensure monthStart used to keep stable memo
    void monthStart;
    return counts;
  }, [month, requests]);

  if (daysInMonth <= 0) {
    return <EmptyState eyebrow="Calendar" title="No calendar data." description="Pick a month to view leave overlays." />;
  }

  const { from } = monthRange(month);
  const start = new Date(`${from}T00:00:00Z`);
  const days = Array.from({ length: daysInMonth }, (_, i) => {
    const d = new Date(start);
    d.setUTCDate(d.getUTCDate() + i);
    return d.toISOString().slice(0, 10);
  });

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {days.map((d) => {
        const count = dayCounts.get(d) ?? 0;
        const highlight = count > 0;
        return (
          <div
            key={d}
            className={[
              "rounded-[22px] border border-border/70 bg-card/70 p-4",
              highlight ? "ring-1 ring-primary/20" : "",
            ].join(" ")}
          >
            <p className="text-sm font-semibold">{d}</p>
            <p className="mt-2 text-xs text-muted-foreground">{count} employee(s) on leave</p>
          </div>
        );
      })}
    </div>
  );
}

