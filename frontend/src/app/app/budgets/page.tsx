"use client";

import { FormEvent, useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useBudgetVariance, useBudgets, useCreateBudget, useUpdateBudget } from "@/features/budgets/hooks";
import { canEdit } from "@/lib/auth/rbac";
import { formatMoney, formatPercent } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";

type BudgetFilter = "ALL" | "EXPENSE" | "REVENUE";

function currentMonth() {
  return new Date().toISOString().slice(0, 7);
}

export default function BudgetsPage() {
  const selectedOrg = useAppStore((s) => s.orgs.find((org) => org.org_id === s.selectedOrgId));
  const role = selectedOrg?.role;
  const editable = canEdit(role);
  const toast = useToast();

  const [month, setMonth] = useState(currentMonth);
  const [budgetFilter, setBudgetFilter] = useState<BudgetFilter>("ALL");
  const [newCategory, setNewCategory] = useState("");
  const [newType, setNewType] = useState<"EXPENSE" | "REVENUE">("EXPENSE");
  const [newAmount, setNewAmount] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [editingBudgetId, setEditingBudgetId] = useState<string | null>(null);
  const [editAmount, setEditAmount] = useState("");
  const [editNotes, setEditNotes] = useState("");

  const period = `${month}-01`;
  const budgets = useBudgets(period, budgetFilter, false);
  const variance = useBudgetVariance(period, budgetFilter);
  const createBudget = useCreateBudget();
  const updateBudget = useUpdateBudget();

  const describeAlertRefresh = (meta?: { taskId: string; status: string; queued: boolean } | null) => {
    if (!meta) return "Alert refresh queued.";
    return meta.queued
      ? `Alert refresh queued (job ${meta.taskId}).`
      : `Alert refresh already pending (job ${meta.taskId}).`;
  };

  const sortedBudgets = useMemo(() => {
    const rows = budgets.data ?? [];
    return [...rows].sort((a, b) => a.category.localeCompare(b.category));
  }, [budgets.data]);

  async function onCreateBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newCategory.trim() || !newAmount.trim()) {
      toast.toast({ title: "Category and amount are required", variant: "danger" });
      return;
    }
    try {
      const result = await createBudget.mutateAsync({
        category: newCategory.trim(),
        period_month: period,
        budget_type: newType,
        planned_amount: String(Number(newAmount)),
        notes: newNotes.trim() || undefined,
      });
      setNewCategory("");
      setNewAmount("");
      setNewNotes("");
      toast.toast({ title: "Budget saved", description: describeAlertRefresh(result.alertRecalc), variant: "success" });
    } catch (err) {
      toast.toast({ title: err instanceof Error ? err.message : "Budget create failed", variant: "danger" });
    }
  }

  async function onSaveEdit() {
    if (!editingBudgetId || !editAmount.trim()) {
      return;
    }
    try {
      const result = await updateBudget.mutateAsync({
        budgetId: editingBudgetId,
        planned_amount: String(Number(editAmount)),
        notes: editNotes.trim() || undefined,
      });
      setEditingBudgetId(null);
      setEditAmount("");
      setEditNotes("");
      toast.toast({ title: "Budget version updated", description: describeAlertRefresh(result.alertRecalc), variant: "success" });
    } catch (err) {
      toast.toast({ title: err instanceof Error ? err.message : "Budget update failed", variant: "danger" });
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Budgets"
        description="Category budgets with month-level variance against actuals."
        actions={
          <>
            <Input
              aria-label="Budget month"
              type="month"
              value={month}
              onChange={(event) => setMonth(event.target.value)}
              className="w-[160px]"
            />
            <div className="w-[160px]">
              <Select value={budgetFilter} onValueChange={(value) => setBudgetFilter(value as BudgetFilter)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All types</SelectItem>
                  <SelectItem value="EXPENSE">Expense</SelectItem>
                  <SelectItem value="REVENUE">Revenue</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Variance summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-muted-foreground">Period: {period}</p>
            <div className="grid gap-2 md:grid-cols-3">
              <div className="rounded-2xl border border-border/70 bg-card/70 p-3">
                <p className="text-xs text-muted-foreground">Planned</p>
                <p className="text-lg font-semibold">{formatMoney(variance.data?.totals.planned_amount)}</p>
              </div>
              <div className="rounded-2xl border border-border/70 bg-card/70 p-3">
                <p className="text-xs text-muted-foreground">Actual</p>
                <p className="text-lg font-semibold">{formatMoney(variance.data?.totals.actual_amount)}</p>
              </div>
              <div className="rounded-2xl border border-border/70 bg-card/70 p-3">
                <p className="text-xs text-muted-foreground">Variance</p>
                <p className="text-lg font-semibold">{formatMoney(variance.data?.totals.variance_amount)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Create budget</CardTitle>
          </CardHeader>
          <CardContent>
            {!editable ? (
              <p className="text-sm text-muted-foreground">Read-only for viewers.</p>
            ) : (
              <form className="grid gap-2 md:grid-cols-2" onSubmit={onCreateBudget}>
                <Input
                  placeholder="Category (e.g. Ops)"
                  value={newCategory}
                  onChange={(event) => setNewCategory(event.target.value)}
                />
                <Select value={newType} onValueChange={(value) => setNewType(value as "EXPENSE" | "REVENUE")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EXPENSE">Expense</SelectItem>
                    <SelectItem value="REVENUE">Revenue</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  placeholder="Planned amount"
                  inputMode="decimal"
                  value={newAmount}
                  onChange={(event) => setNewAmount(event.target.value)}
                />
                <Input
                  placeholder="Notes (optional)"
                  value={newNotes}
                  onChange={(event) => setNewNotes(event.target.value)}
                />
                <div className="md:col-span-2">
                  <Button type="submit" disabled={createBudget.isPending}>
                    Save budget
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Current budgets</CardTitle>
        </CardHeader>
        <CardContent>
          {sortedBudgets.length === 0 ? (
            <EmptyState
              eyebrow="No budgets yet"
              title="Create your first monthly budget."
              description="Budgets are versioned per org, category, month, and budget type."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="py-2">Category</th>
                    <th className="py-2">Type</th>
                    <th className="py-2">Planned</th>
                    <th className="py-2">Version</th>
                    <th className="py-2">Notes</th>
                    <th className="py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedBudgets.map((budget) => {
                    const isEditing = editingBudgetId === budget.id;
                    return (
                      <tr key={budget.id} className="border-t border-border/60">
                        <td className="py-3 font-medium">{budget.category}</td>
                        <td><Badge variant="secondary">{budget.budget_type}</Badge></td>
                        <td>{formatMoney(budget.planned_amount)}</td>
                        <td>v{budget.version}</td>
                        <td className="max-w-[280px] truncate text-muted-foreground">{budget.notes || "-"}</td>
                        <td>
                          {!editable ? (
                            <span className="text-xs text-muted-foreground">Read-only</span>
                          ) : isEditing ? (
                            <div className="flex min-w-[380px] flex-wrap items-center gap-2">
                              <Input
                                className="w-[140px]"
                                placeholder="Amount"
                                value={editAmount}
                                onChange={(event) => setEditAmount(event.target.value)}
                              />
                              <Input
                                className="w-[180px]"
                                placeholder="Notes"
                                value={editNotes}
                                onChange={(event) => setEditNotes(event.target.value)}
                              />
                              <Button size="sm" onClick={onSaveEdit} disabled={updateBudget.isPending}>Save</Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  setEditingBudgetId(null);
                                  setEditAmount("");
                                  setEditNotes("");
                                }}
                              >
                                Cancel
                              </Button>
                            </div>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setEditingBudgetId(budget.id);
                                setEditAmount(budget.planned_amount);
                                setEditNotes(budget.notes || "");
                              }}
                            >
                              New version
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Variance lines</CardTitle>
        </CardHeader>
        <CardContent>
          {(variance.data?.lines.length || 0) === 0 ? (
            <p className="text-sm text-muted-foreground">No variance data for this period and filter.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="py-2">Category</th>
                    <th className="py-2">Type</th>
                    <th className="py-2">Planned</th>
                    <th className="py-2">Actual</th>
                    <th className="py-2">Variance</th>
                    <th className="py-2">Variance %</th>
                  </tr>
                </thead>
                <tbody>
                  {variance.data?.lines.map((line) => (
                    <tr key={`${line.budget_type}-${line.category}`} className="border-t border-border/60">
                      <td className="py-3 font-medium">{line.category}</td>
                      <td><Badge variant="outline">{line.budget_type}</Badge></td>
                      <td>{formatMoney(line.planned_amount)}</td>
                      <td>{formatMoney(line.actual_amount)}</td>
                      <td>{formatMoney(line.variance_amount)}</td>
                      <td>{line.variance_pct ? formatPercent(line.variance_pct) : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
