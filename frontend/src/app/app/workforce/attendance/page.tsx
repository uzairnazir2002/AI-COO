"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionHeader } from "@/components/common/section-header";
import { TabNav } from "@/components/layout/tab-nav";
import { PermissionState } from "@/components/states/permission-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { canEdit } from "@/lib/auth/rbac";
import { formatMonth, startOfMonthISO, todayISO } from "@/lib/utils/format";
import {
  useClockIn,
  useClockOut,
  useCreateWorkforceShift,
  useCreateWorkforceShiftAssignment,
  useDeactivateWorkforceShift,
  useManualAttendanceEntry,
  useRequestCorrection,
  useReviewCorrection,
  useUpdateWorkforceShift,
  useWorkforceAttendanceCalendar,
  useWorkforceAttendanceDaily,
  useWorkforceCorrections,
  useWorkforceEmployees,
  useWorkforceShiftAssignments,
  useWorkforceShifts,
} from "@/features/workforce/hooks";
import { useAppStore } from "@/store/appStore";

const ATTENDANCE_STATUSES = [
  "PRESENT",
  "ABSENT",
  "LATE",
  "HALF_DAY",
  "LEAVE",
  "HOLIDAY",
  "REMOTE",
  "WEEKEND_OFF",
] as const;

/** Radix Select forbids `value=""` on items; use this sentinel for “all employees”. */
const ALL_EMPLOYEES_FILTER = "__all__";

export default function WorkforceAttendancePage() {
  const searchParams = useSearchParams();
  const selectedOrg = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId));
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = selectedOrg?.role;
  const canMutate = canEdit(role);

  const [tab, setTab] = useState(() => searchParams.get("tab") || "daily");
  const [day, setDay] = useState(() => searchParams.get("day") || todayISO());
  const [month, setMonth] = useState(() => searchParams.get("month") || startOfMonthISO().slice(0, 7));
  const [employeeFilterId, setEmployeeFilterId] = useState(() => searchParams.get("employee_id") || ALL_EMPLOYEES_FILTER);

  const employees = useWorkforceEmployees({ include_inactive: false, limit: 500 });
  const dailyEmployeeId = employeeFilterId === ALL_EMPLOYEES_FILTER ? undefined : employeeFilterId;
  const daily = useWorkforceAttendanceDaily(day, dailyEmployeeId);
  const calendar = useWorkforceAttendanceCalendar(month);
  const shifts = useWorkforceShifts(true);
  const assignments = useWorkforceShiftAssignments({ as_of: day, limit: 500 });
  const corrections = useWorkforceCorrections({ status: tab === "corrections" ? "PENDING" : undefined, limit: 200 });

  const clockIn = useClockIn();
  const clockOut = useClockOut();
  const manual = useManualAttendanceEntry();
  const requestCorrection = useRequestCorrection();
  const reviewCorrection = useReviewCorrection();

  const employeeIndex = useMemo(() => new Map((employees.data ?? []).map((e) => [e.id, e])), [employees.data]);
  const shiftIndex = useMemo(() => new Map((shifts.data ?? []).map((s) => [s.id, s])), [shifts.data]);

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="Attendance"
        title="Select an organization to manage attendance."
        description="Attendance is org-scoped. Choose an organization from the header to continue."
        actions={[{ label: "Back to workforce", href: "/app/workforce" }]}
      />
    );
  }

  const topError =
    (employees.error as Error | undefined)?.message ||
    (daily.error as Error | undefined)?.message ||
    (calendar.error as Error | undefined)?.message ||
    (shifts.error as Error | undefined)?.message ||
    (assignments.error as Error | undefined)?.message ||
    (corrections.error as Error | undefined)?.message;
  if (topError) {
    return (
      <ErrorState
        title="Attendance failed to load"
        description={topError}
        onRetry={() => {
          void employees.refetch();
          void daily.refetch();
          void calendar.refetch();
          void shifts.refetch();
          void assignments.refetch();
          void corrections.refetch();
        }}
      />
    );
  }

  const loading = employees.isLoading;

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Workforce"
        title="Attendance"
        description="Daily log, calendar view, shifts, and correction approvals."
        actions={
          !canMutate ? <PermissionState message="Read-only access. Owners and editors can create and adjust attendance." /> : undefined
        }
      />

      <TabNav
        active={tab}
        onChange={setTab}
        items={[
          { id: "daily", label: "Daily log" },
          { id: "calendar", label: "Calendar" },
          { id: "shifts", label: "Shifts" },
          { id: "corrections", label: "Corrections" },
        ]}
        ariaLabel="Attendance sections"
      />

      {tab === "daily" ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <Input type="date" value={day} onChange={(e) => setDay(e.target.value)} className="h-10 w-44" />
              <div className="w-[260px]">
                <Select value={employeeFilterId} onValueChange={setEmployeeFilterId}>
                  <SelectTrigger><SelectValue placeholder="All employees" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL_EMPLOYEES_FILTER}>All employees</SelectItem>
                    {(employees.data ?? []).map((e) => (
                      <SelectItem key={e.id} value={e.id}>
                        {e.first_name} {e.last_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <p className="text-sm text-muted-foreground">
                Tip: use manual entry for absences, holidays, and remote days.
              </p>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link href="/app/workforce/employees">Employees</Link>
            </Button>
          </div>

          {loading || daily.isLoading ? (
            <Skeleton className="h-64 w-full rounded-[28px]" />
          ) : (daily.data?.items?.length ?? 0) === 0 ? (
            <EmptyState
              eyebrow="Daily log"
              title="No attendance records for this date."
              description="Clock in/out employees or add manual records."
            />
          ) : (
            <div className="grid gap-3">
              {(daily.data?.items ?? []).map((row) => {
                const emp = employeeIndex.get(row.employee_id);
                const shift = row.shift_id ? shiftIndex.get(row.shift_id) : null;
                return (
                  <Card key={row.id}>
                    <CardHeader className="flex flex-row items-center justify-between gap-3">
                      <div className="min-w-0">
                        <CardTitle className="truncate">
                          {emp ? `${emp.first_name} ${emp.last_name}` : row.employee_id}
                        </CardTitle>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {row.status} · {row.source}
                          {shift ? ` · Shift: ${shift.name}` : ""}
                          {row.is_late ? ` · Late by ${row.minutes_late}m` : ""}
                          {row.missing_checkout ? " · Missing checkout" : ""}
                        </p>
                      </div>
                      {canMutate ? (
                        <div className="flex shrink-0 flex-wrap gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={clockIn.isPending}
                            onClick={async () => {
                              await clockIn.mutateAsync({ employee_id: row.employee_id });
                            }}
                          >
                            Clock in
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={clockOut.isPending}
                            onClick={async () => {
                              await clockOut.mutateAsync({ employee_id: row.employee_id });
                            }}
                          >
                            Clock out
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={requestCorrection.isPending}
                            onClick={async () => {
                              await requestCorrection.mutateAsync({
                                attendance_record_id: row.id,
                                reason: "Correction requested from daily log",
                              });
                            }}
                          >
                            Request correction
                          </Button>
                        </div>
                      ) : null}
                    </CardHeader>
                    <CardContent className="grid gap-2 text-sm md:grid-cols-3">
                      <Detail label="Clock in" value={row.clock_in_at ?? "—"} />
                      <Detail label="Clock out" value={row.clock_out_at ?? "—"} />
                      <Detail label="Worked" value={`${row.worked_minutes} min`} />
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {canMutate ? (
            <ManualEntryCard
              employees={employees.data ?? []}
              day={day}
              pending={manual.isPending}
              onSubmit={async (payload) => {
                await manual.mutateAsync(payload);
              }}
            />
          ) : null}
        </div>
      ) : null}

      {tab === "calendar" ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="h-10 w-44" />
              <p className="text-sm text-muted-foreground">Monthly totals by status.</p>
            </div>
            <p className="text-sm text-muted-foreground">{formatMonth(month)}</p>
          </div>

          {calendar.isLoading ? (
            <Skeleton className="h-64 w-full rounded-[28px]" />
          ) : (
            <CalendarGrid days={calendar.data?.days ?? []} onPickDay={(d) => { setDay(d); setTab("daily"); }} />
          )}
        </div>
      ) : null}

      {tab === "shifts" ? (
        <ShiftsPanel
          canMutate={canMutate}
          employees={employees.data ?? []}
          shifts={shifts.data ?? []}
          assignments={assignments.data ?? []}
        />
      ) : null}

      {tab === "corrections" ? (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Pending correction requests. Approving applies the proposed changes to the attendance record.
          </p>

          {corrections.isLoading ? (
            <Skeleton className="h-64 w-full rounded-[28px]" />
          ) : (corrections.data ?? []).length === 0 ? (
            <EmptyState
              eyebrow="Corrections"
              title="No pending corrections."
              description="Correction requests will appear here for review."
            />
          ) : (
            <div className="grid gap-3">
              {(corrections.data ?? []).map((c) => {
                const emp = employeeIndex.get(c.employee_id);
                return (
                  <Card key={c.id}>
                    <CardHeader>
                      <CardTitle className="truncate">
                        {emp ? `${emp.first_name} ${emp.last_name}` : c.employee_id} · {c.status}
                      </CardTitle>
                      <p className="mt-1 text-sm text-muted-foreground">{c.reason}</p>
                    </CardHeader>
                    <CardContent className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm text-muted-foreground">
                        Proposed: {c.proposed_status ?? "—"} · in {c.proposed_clock_in_at ?? "—"} · out{" "}
                        {c.proposed_clock_out_at ?? "—"}
                      </div>
                      {canMutate ? (
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={reviewCorrection.isPending}
                            onClick={async () => {
                              await reviewCorrection.mutateAsync({ id: c.id, status: "APPROVED" });
                            }}
                          >
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={reviewCorrection.isPending}
                            onClick={async () => {
                              await reviewCorrection.mutateAsync({ id: c.id, status: "REJECTED" });
                            }}
                          >
                            Reject
                          </Button>
                        </div>
                      ) : null}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card/60 px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate font-medium">{value}</p>
    </div>
  );
}

function ManualEntryCard({
  employees,
  day,
  pending,
  onSubmit,
}: {
  employees: Array<{ id: string; first_name: string; last_name: string }>;
  day: string;
  pending: boolean;
  onSubmit: (payload: { employee_id: string; work_date: string; status: string; clock_in_at?: string | null; clock_out_at?: string | null; notes?: string | null }) => Promise<void>;
}) {
  const [employeeId, setEmployeeId] = useState<string>(employees[0]?.id ?? "");
  const [status, setStatus] = useState<(typeof ATTENDANCE_STATUSES)[number]>("PRESENT");
  const [notes, setNotes] = useState("");
  const [clockInAt, setClockInAt] = useState<string>("");
  const [clockOutAt, setClockOutAt] = useState<string>("");
  return (
    <Card>
      <CardHeader>
        <CardTitle>Manual entry</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="grid gap-2">
            <label className="text-sm font-medium">Employee</label>
            <Select value={employeeId} onValueChange={setEmployeeId}>
              <SelectTrigger><SelectValue placeholder="Select employee" /></SelectTrigger>
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
            <label className="text-sm font-medium">Status</label>
            <Select value={status} onValueChange={(v) => setStatus(v as (typeof ATTENDANCE_STATUSES)[number])}>
              <SelectTrigger><SelectValue placeholder="Select status" /></SelectTrigger>
              <SelectContent>
                {ATTENDANCE_STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Clock in (optional)</label>
            <Input type="datetime-local" value={clockInAt} onChange={(e) => setClockInAt(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Clock out (optional)</label>
            <Input type="datetime-local" value={clockOutAt} onChange={(e) => setClockOutAt(e.target.value)} />
          </div>
        </div>

        <div className="grid gap-2">
          <label className="text-sm font-medium">Notes (optional)</label>
          <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. Holiday adjustment" />
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            disabled={pending || !employeeId}
            onClick={async () => {
              const toIso = (v: string) => (v ? new Date(v).toISOString() : null);
              await onSubmit({
                employee_id: employeeId,
                work_date: day,
                status,
                clock_in_at: toIso(clockInAt),
                clock_out_at: toIso(clockOutAt),
                notes: notes || null,
              });
              setNotes("");
              setClockInAt("");
              setClockOutAt("");
            }}
          >
            Add record
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function CalendarGrid({
  days,
  onPickDay,
}: {
  days: Array<{ date: string; totals: Record<string, number>; late_count: number; missing_checkout_count: number }>;
  onPickDay: (day: string) => void;
}) {
  if (days.length === 0) {
    return <EmptyState eyebrow="Calendar" title="No calendar data." description="Add attendance records to populate the month view." />;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {days.map((d) => {
        const present = d.totals["PRESENT"] ?? 0;
        const late = d.totals["LATE"] ?? 0;
        const absent = d.totals["ABSENT"] ?? 0;
        const highlight = d.late_count > 0 || d.missing_checkout_count > 0;
        return (
          <button
            key={d.date}
            type="button"
            onClick={() => onPickDay(d.date)}
            className={[
              "text-left rounded-[22px] border border-border/70 bg-card/70 p-4 transition hover:border-primary/30 hover:shadow-sm",
              highlight ? "ring-1 ring-warning/30" : "",
            ].join(" ")}
          >
            <p className="text-sm font-semibold">{d.date}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Present {present} · Late {late} · Absent {absent}
            </p>
            {d.late_count > 0 ? <p className="mt-2 text-xs text-warning">Late flags: {d.late_count}</p> : null}
            {d.missing_checkout_count > 0 ? (
              <p className="mt-1 text-xs text-warning">Missing checkout: {d.missing_checkout_count}</p>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

function ShiftsPanel({
  canMutate,
  employees,
  shifts,
  assignments,
}: {
  canMutate: boolean;
  employees: Array<{ id: string; first_name: string; last_name: string }>;
  shifts: Array<{ id: string; name: string; start_time: string; end_time: string; grace_minutes: number; is_active: boolean }>;
  assignments: Array<{ id: string; employee_id: string; shift_id: string; effective_from: string; effective_to: string | null }>;
}) {
  const createShift = useCreateWorkforceShift();
  const updateShift = useUpdateWorkforceShift();
  const deactivateShift = useDeactivateWorkforceShift();
  const createAssignment = useCreateWorkforceShiftAssignment();

  const [createName, setCreateName] = useState("");
  const [createStart, setCreateStart] = useState("09:00");
  const [createEnd, setCreateEnd] = useState("18:00");
  const [createGrace, setCreateGrace] = useState("5");

  const [assignEmployeeId, setAssignEmployeeId] = useState<string>(employees[0]?.id ?? "");
  const [assignShiftId, setAssignShiftId] = useState<string>(shifts[0]?.id ?? "");
  const [assignFrom, setAssignFrom] = useState<string>(todayISO());
  const [assignTo, setAssignTo] = useState<string>("");

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Shifts and assignments power lateness detection.
      </p>
      {!canMutate ? <PermissionState message="Read-only access. Owners and editors can manage shifts." /> : null}
      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle>Shifts</CardTitle>
            {canMutate ? (
              <Dialog>
                <DialogTrigger asChild>
                  <Button size="sm" variant="outline">
                    New shift
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create shift</DialogTitle>
                  </DialogHeader>
                  <div className="grid gap-3">
                    <div className="grid gap-2">
                      <label className="text-sm font-medium">Name</label>
                      <Input value={createName} onChange={(e) => setCreateName(e.target.value)} placeholder="e.g. General" />
                    </div>
                    <div className="grid gap-3 md:grid-cols-3">
                      <div className="grid gap-2">
                        <label className="text-sm font-medium">Start</label>
                        <Input type="time" value={createStart} onChange={(e) => setCreateStart(e.target.value)} />
                      </div>
                      <div className="grid gap-2">
                        <label className="text-sm font-medium">End</label>
                        <Input type="time" value={createEnd} onChange={(e) => setCreateEnd(e.target.value)} />
                      </div>
                      <div className="grid gap-2">
                        <label className="text-sm font-medium">Grace (minutes)</label>
                        <Input value={createGrace} onChange={(e) => setCreateGrace(e.target.value)} inputMode="numeric" />
                      </div>
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <Button
                      disabled={createShift.isPending || !createName.trim()}
                      onClick={async () => {
                        await createShift.mutateAsync({
                          name: createName,
                          start_time: createStart,
                          end_time: createEnd,
                          grace_minutes: Number.isFinite(Number(createGrace)) ? Number(createGrace) : 5,
                        });
                        setCreateName("");
                      }}
                    >
                      Create
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {shifts.length === 0 ? <p className="text-muted-foreground">No shifts yet.</p> : null}
            {shifts.map((s) => (
              <div key={s.id} className="rounded-2xl border border-border/70 bg-card/60 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-medium">{s.name}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {s.start_time} → {s.end_time} · grace {s.grace_minutes}m · {s.is_active ? "active" : "inactive"}
                    </p>
                  </div>
                  {canMutate ? (
                    <div className="flex gap-2">
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button size="sm" variant="outline">
                            Edit
                          </Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Edit shift</DialogTitle>
                          </DialogHeader>
                          <ShiftEditForm
                            shift={s}
                            pending={updateShift.isPending}
                            onSave={async (payload) => {
                              await updateShift.mutateAsync({ id: s.id, ...payload });
                            }}
                          />
                        </DialogContent>
                      </Dialog>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={deactivateShift.isPending || !s.is_active}
                        onClick={async () => {
                          await deactivateShift.mutateAsync(s.id);
                        }}
                      >
                        Deactivate
                      </Button>
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle>Assignments (as-of selected date)</CardTitle>
            <p className="text-sm text-muted-foreground">Assign a shift to an employee to enable expected start time + grace.</p>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {canMutate ? (
              <div className="mb-3 grid gap-3 rounded-[22px] border border-border/70 bg-card/60 p-3">
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="grid gap-2">
                    <label className="text-sm font-medium">Employee</label>
                    <Select value={assignEmployeeId} onValueChange={setAssignEmployeeId}>
                      <SelectTrigger><SelectValue placeholder="Select employee" /></SelectTrigger>
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
                    <label className="text-sm font-medium">Shift</label>
                    <Select value={assignShiftId} onValueChange={setAssignShiftId}>
                      <SelectTrigger><SelectValue placeholder="Select shift" /></SelectTrigger>
                      <SelectContent>
                        {shifts.filter((s) => s.is_active).map((s) => (
                          <SelectItem key={s.id} value={s.id}>
                            {s.name} ({s.start_time}–{s.end_time})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="grid gap-2">
                    <label className="text-sm font-medium">Effective from</label>
                    <Input type="date" value={assignFrom} onChange={(e) => setAssignFrom(e.target.value)} />
                  </div>
                  <div className="grid gap-2">
                    <label className="text-sm font-medium">Effective to (optional)</label>
                    <Input type="date" value={assignTo} onChange={(e) => setAssignTo(e.target.value)} />
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button
                    size="sm"
                    disabled={createAssignment.isPending || !assignEmployeeId || !assignShiftId || !assignFrom}
                    onClick={async () => {
                      await createAssignment.mutateAsync({
                        employee_id: assignEmployeeId,
                        shift_id: assignShiftId,
                        effective_from: assignFrom,
                        effective_to: assignTo || null,
                      });
                    }}
                  >
                    Assign shift
                  </Button>
                </div>
              </div>
            ) : null}
            {assignments.length === 0 ? <p className="text-muted-foreground">No assignments for this date.</p> : null}
            {assignments.map((a) => {
              const emp = employees.find((e) => e.id === a.employee_id);
              const shift = shifts.find((s) => s.id === a.shift_id);
              return (
                <div key={a.id} className="rounded-2xl border border-border/70 bg-card/60 p-3">
                  <p className="font-medium">{emp ? `${emp.first_name} ${emp.last_name}` : a.employee_id}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {shift ? shift.name : a.shift_id} · from {a.effective_from}{a.effective_to ? ` to ${a.effective_to}` : ""}
                  </p>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ShiftEditForm({
  shift,
  pending,
  onSave,
}: {
  shift: { name: string; start_time: string; end_time: string; grace_minutes: number; is_active: boolean };
  pending: boolean;
  onSave: (payload: { name: string; start_time: string; end_time: string; grace_minutes: number; is_active: boolean }) => Promise<void>;
}) {
  const [name, setName] = useState(shift.name);
  const [start, setStart] = useState(shift.start_time);
  const [end, setEnd] = useState(shift.end_time);
  const [grace, setGrace] = useState(String(shift.grace_minutes ?? 5));
  const [active, setActive] = useState(shift.is_active ? "true" : "false");
  return (
    <>
      <div className="grid gap-3">
        <div className="grid gap-2">
          <label className="text-sm font-medium">Name</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <div className="grid gap-2">
            <label className="text-sm font-medium">Start</label>
            <Input type="time" value={start} onChange={(e) => setStart(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">End</label>
            <Input type="time" value={end} onChange={(e) => setEnd(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium">Grace (minutes)</label>
            <Input value={grace} onChange={(e) => setGrace(e.target.value)} inputMode="numeric" />
          </div>
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-medium">Status</label>
          <Select value={active} onValueChange={setActive}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="true">Active</SelectItem>
              <SelectItem value="false">Inactive</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="mt-6 flex justify-end">
        <Button
          disabled={pending || !name.trim()}
          onClick={async () => {
            await onSave({
              name,
              start_time: start,
              end_time: end,
              grace_minutes: Number.isFinite(Number(grace)) ? Number(grace) : 5,
              is_active: active === "true",
            });
          }}
        >
          Save
        </Button>
      </div>
    </>
  );
}

