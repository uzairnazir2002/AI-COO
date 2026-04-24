"use client";

import { useId, useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { useToast } from "@/components/common/use-toast";
import { SectionHeader } from "@/components/common/section-header";
import { PermissionState } from "@/components/states/permission-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetchRaw } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { canEdit, isOwner } from "@/lib/auth/rbac";
import { formatMoney, todayISO } from "@/lib/utils/format";
import {
  useApproveWorkforcePayrollPeriod,
  useCreateWorkforcePayrollAdjustment,
  useCreateWorkforcePayrollPeriod,
  useDeleteWorkforcePayrollAdjustment,
  useGenerateWorkforcePayrollDraft,
  useMarkPaidWorkforcePayrollPeriod,
  useWorkforceEmployees,
  useWorkforcePayrollEntries,
  useWorkforcePayrollPeriods,
  useWorkforcePayslipPreview,
} from "@/features/workforce/hooks";
import type { WorkforcePayrollAdjustment, WorkforcePayrollEntry } from "@/types/domain";
import { useAppStore } from "@/store/appStore";

export default function WorkforcePayrollPage() {
  const { toast } = useToast();
  const selectedOrg = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId));
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = selectedOrg?.role;
  const canMutate = canEdit(role);
  const canMarkPaid = isOwner(role);

  const periods = useWorkforcePayrollPeriods();
  const employees = useWorkforceEmployees({ include_inactive: false, limit: 5000 });

  const [activePeriodId, setActivePeriodId] = useState<string>("");
  const entries = useWorkforcePayrollEntries(activePeriodId);

  const createPeriod = useCreateWorkforcePayrollPeriod();
  const generate = useGenerateWorkforcePayrollDraft();
  const approve = useApproveWorkforcePayrollPeriod();
  const markPaid = useMarkPaidWorkforcePayrollPeriod();

  const employeeIndex = useMemo(
    () => new Map((employees.data ?? []).map((e) => [e.id, `${e.first_name} ${e.last_name}`])),
    [employees.data],
  );

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="Payroll"
        title="Select an organization to manage payroll."
        description="Payroll is org-scoped. Choose an organization from the header to continue."
        actions={[{ label: "Back to workforce", href: "/app/workforce" }]}
      />
    );
  }

  const topError =
    (periods.error as Error | undefined)?.message ||
    (employees.error as Error | undefined)?.message ||
    (entries.error as Error | undefined)?.message;
  if (topError) {
    return (
      <ErrorState
        title="Payroll failed to load"
        description={topError}
        onRetry={() => {
          void periods.refetch();
          void employees.refetch();
          void entries.refetch();
        }}
      />
    );
  }

  const selectedPeriod = (periods.data ?? []).find((p) => p.id === activePeriodId) ?? null;

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Workforce"
        title="Payroll"
        description="Create payroll periods, generate drafts from attendance, apply adjustments, and approve. Owners mark periods as paid once funds are disbursed."
        actions={!canMutate ? <PermissionState message="Read-only access. Owners and editors can manage payroll." /> : undefined}
      />

      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="grid gap-2">
          <p className="text-sm font-medium">Payroll period</p>
          <div className="flex flex-wrap gap-2">
            <div className="w-full sm:w-[280px]">
              <Select value={activePeriodId} onValueChange={setActivePeriodId}>
                <SelectTrigger><SelectValue placeholder="Select a period" /></SelectTrigger>
                <SelectContent>
                  {(periods.data ?? []).map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.start_date} → {p.end_date} · {p.status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {canMutate ? (
              <NewPeriodDialog
                onCreate={async (start_date, end_date) => {
                  const created = await createPeriod.mutateAsync({ start_date, end_date });
                  setActivePeriodId(created.id);
                }}
                pending={createPeriod.isPending}
              />
            ) : null}
          </div>
        </div>

        {selectedPeriod ? (
          <div className="flex flex-wrap gap-2">
            {canMutate ? (
              <>
                <Button
                  variant="outline"
                  disabled={generate.isPending || selectedPeriod.status !== "DRAFT"}
                  onClick={async () => {
                    try {
                      await generate.mutateAsync({ payroll_period_id: selectedPeriod.id, overtime_multiplier: "1.5" });
                    } catch (err) {
                      toast({
                        title: err instanceof Error ? err.message : "Generate draft failed",
                        variant: "danger",
                      });
                    }
                  }}
                >
                  Generate draft
                </Button>
                <Button
                  variant="outline"
                  disabled={approve.isPending || selectedPeriod.status !== "DRAFT"}
                  onClick={async () => {
                    try {
                      await approve.mutateAsync(selectedPeriod.id);
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
                {canMarkPaid ? (
                  <Button
                    variant="outline"
                    disabled={markPaid.isPending || selectedPeriod.status !== "APPROVED"}
                    onClick={async () => {
                      try {
                        await markPaid.mutateAsync(selectedPeriod.id);
                      } catch (err) {
                        toast({
                          title: err instanceof Error ? err.message : "Mark paid failed",
                          variant: "danger",
                        });
                      }
                    }}
                  >
                    Mark paid
                  </Button>
                ) : null}
              </>
            ) : null}
            <Button
              variant="outline"
              onClick={() => {
                void downloadPayrollCsv(selectedPeriod.id, orgId).catch((err) => {
                  toast({
                    title: err instanceof Error ? err.message : "Export failed",
                    variant: "danger",
                  });
                });
              }}
            >
              Export CSV
            </Button>
            {selectedPeriod.status === "APPROVED" && canMutate && !canMarkPaid ? (
              <p className="w-full text-xs text-muted-foreground md:w-auto md:self-center">
                Only an owner can mark this period as paid.
              </p>
            ) : null}
          </div>
        ) : null}
      </div>

      {!activePeriodId ? (
        <EmptyState
          eyebrow="Payroll"
          title="Select a payroll period."
          description="Create a period, then generate draft entries from attendance."
        />
      ) : entries.isLoading ? (
        <Skeleton className="h-64 w-full rounded-[28px]" />
      ) : (entries.data ?? []).length === 0 ? (
        <EmptyState
          eyebrow="Entries"
          title="No payroll entries yet."
          description={selectedPeriod?.status === "DRAFT" ? "Generate a draft to populate entries." : "No entries exist for this period."}
        />
      ) : (
        <div className="grid gap-3">
          {(entries.data ?? []).map((e) => (
            <PayrollEntryCard
              key={e.id}
              employeeName={employeeIndex.get(e.employee_id) ?? e.employee_id}
              periodId={activePeriodId}
              orgId={orgId}
              entry={e}
              canMutate={canMutate && selectedPeriod?.status === "DRAFT"}
              canRemoveAdjustments={canMutate && selectedPeriod?.status === "DRAFT"}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function NewPeriodDialog({ onCreate, pending }: { onCreate: (start: string, end: string) => Promise<unknown>; pending: boolean }) {
  const [open, setOpen] = useState(false);
  const [start, setStart] = useState(todayISO());
  const [end, setEnd] = useState(todayISO());
  const startId = useId();
  const endId = useId();
  const { toast } = useToast();
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">New period</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>Create payroll period</DialogTitle></DialogHeader>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="grid gap-2">
            <label htmlFor={startId} className="text-sm font-medium">
              Start date
            </label>
            <Input id={startId} type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <label htmlFor={endId} className="text-sm font-medium">
              End date
            </label>
            <Input id={endId} type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <Button
            disabled={pending || !start || !end}
            onClick={async () => {
              try {
                await onCreate(start, end);
                setOpen(false);
              } catch (err) {
                toast({
                  title: err instanceof Error ? err.message : "Could not create payroll period",
                  variant: "danger",
                });
              }
            }}
          >
            Create
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

async function downloadPayrollCsv(periodId: string, orgId: string) {
  const path = `${apiPaths.workforcePayrollExport(periodId)}?org_id=${encodeURIComponent(orgId)}`;
  const res = await apiFetchRaw(path);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `payroll-${periodId}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

async function downloadPayrollPdf(entryId: string, orgId: string) {
  const path = `${apiPaths.workforcePayrollPayslipPdf(entryId)}?org_id=${encodeURIComponent(orgId)}`;
  const res = await apiFetchRaw(path);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `payslip-${entryId}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}

function moneyOrDash(value: string | null | undefined) {
  if (value == null || value === "") return "—";
  return formatMoney(value);
}

function PayrollEntryCard({
  employeeName,
  periodId,
  orgId,
  entry,
  canMutate,
  canRemoveAdjustments,
}: {
  employeeName: string;
  periodId: string;
  orgId: string;
  entry: WorkforcePayrollEntry;
  canMutate: boolean;
  canRemoveAdjustments: boolean;
}) {
  const { toast } = useToast();
  const payslip = useWorkforcePayslipPreview(entry.id);
  const createAdj = useCreateWorkforcePayrollAdjustment();
  const deleteAdj = useDeleteWorkforcePayrollAdjustment();

  const [kind, setKind] = useState("BONUS");
  const [amount, setAmount] = useState("0");
  const [label, setLabel] = useState("");

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div className="min-w-0">
          <CardTitle className="truncate">{employeeName}</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            {entry.salary_type} · {entry.payable_hours != null ? `${entry.payable_hours}h` : "—"} · overtime {Math.round(entry.overtime_minutes / 60)}h
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm text-muted-foreground">Net</p>
          <p className="text-lg font-semibold">{moneyOrDash(entry.net_pay)}</p>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div
          className={`grid gap-2 text-sm ${entry.salary_type === "SALARIED" ? "md:grid-cols-4" : "md:grid-cols-3"}`}
        >
          <Detail label="Gross" value={moneyOrDash(entry.gross_pay)} />
          {entry.salary_type === "SALARIED" ? (
            <Detail label="Unpaid leave" value={moneyOrDash(entry.unpaid_leave_deduction)} />
          ) : null}
          <Detail label="Adjustments" value={moneyOrDash(entry.adjustments_total)} />
          <Detail label="Net" value={moneyOrDash(entry.net_pay)} />
        </div>

        {canMutate ? (
          <div className="grid gap-2 rounded-[22px] border border-border/70 bg-card/60 p-3 md:grid-cols-[160px_140px_1fr_auto]">
            <Select value={kind} onValueChange={setKind}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {["BONUS", "DEDUCTION", "ADVANCE", "REIMBURSEMENT"].map((k) => (
                  <SelectItem key={k} value={k}>{k}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="decimal" placeholder="Amount" />
            <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Label (optional)" />
            <Button
              disabled={createAdj.isPending}
              onClick={async () => {
                try {
                  await createAdj.mutateAsync({
                    payroll_period_id: periodId,
                    payroll_entry_id: entry.id,
                    employee_id: entry.employee_id,
                    kind,
                    amount,
                    label: label || null,
                  });
                  setAmount("0");
                  setLabel("");
                } catch (err) {
                  toast({
                    title: err instanceof Error ? err.message : "Could not add adjustment",
                    variant: "danger",
                  });
                }
              }}
            >
              Add
            </Button>
          </div>
        ) : null}

        {payslip.isLoading ? (
          <Skeleton className="h-20 w-full rounded-[22px]" />
        ) : payslip.data ? (
          <PayslipPreviewBlock
            preview={payslip.data}
            periodId={periodId}
            payrollEntryId={entry.id}
            orgId={orgId}
            canRemoveAdjustments={canRemoveAdjustments}
            deleteAdj={deleteAdj}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

function PayslipPreviewBlock({
  preview,
  periodId,
  payrollEntryId,
  orgId,
  canRemoveAdjustments,
  deleteAdj,
}: {
  preview: { period: { start_date: string; end_date: string; status: string }; entry: WorkforcePayrollEntry; adjustments: WorkforcePayrollAdjustment[] };
  periodId: string;
  payrollEntryId: string;
  orgId: string;
  canRemoveAdjustments: boolean;
  deleteAdj: ReturnType<typeof useDeleteWorkforcePayrollAdjustment>;
}) {
  const { toast } = useToast();
  const e = preview.entry;
  return (
    <div className="rounded-[22px] border border-border/70 bg-card/60 p-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium text-foreground">Payslip preview</p>
          <p className="mt-1 text-muted-foreground">
            Period {preview.period.start_date} → {preview.period.end_date} · {preview.period.status}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            void downloadPayrollPdf(payrollEntryId, orgId).catch((err) => {
              toast({
                title: err instanceof Error ? err.message : "Download failed",
                variant: "danger",
              });
            });
          }}
        >
          Download PDF
        </Button>
      </div>
      <div className={`mt-3 grid gap-2 ${e.salary_type === "SALARIED" ? "md:grid-cols-4" : "md:grid-cols-3"}`}>
        <Detail label="Gross" value={moneyOrDash(e.gross_pay)} />
        {e.salary_type === "SALARIED" ? <Detail label="Unpaid leave" value={moneyOrDash(e.unpaid_leave_deduction)} /> : null}
        <Detail label="Adjustments" value={moneyOrDash(e.adjustments_total)} />
        <Detail label="Net" value={moneyOrDash(e.net_pay)} />
      </div>
      <p className="mt-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">Line items</p>
      {preview.adjustments.length === 0 ? (
        <p className="mt-1 text-muted-foreground">No adjustments for this entry.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {preview.adjustments.map((adj) => (
            <li key={adj.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border/60 bg-background/40 px-3 py-2">
              <span>
                <span className="font-medium text-foreground">{adj.kind}</span>
                {adj.label ? <span className="text-muted-foreground"> · {adj.label}</span> : null}
              </span>
              <span className="flex items-center gap-2">
                <span className="tabular-nums">{adj.amount != null ? formatMoney(adj.amount) : "—"}</span>
                {canRemoveAdjustments ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 text-destructive hover:text-destructive"
                    disabled={deleteAdj.isPending}
                    onClick={async () => {
                      try {
                        await deleteAdj.mutateAsync({
                          adjustment_id: adj.id,
                          payroll_period_id: periodId,
                          payroll_entry_id: payrollEntryId,
                        });
                      } catch (err) {
                        toast({
                          title: err instanceof Error ? err.message : "Could not remove adjustment",
                          variant: "danger",
                        });
                      }
                    }}
                  >
                    Remove
                  </Button>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      )}
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

