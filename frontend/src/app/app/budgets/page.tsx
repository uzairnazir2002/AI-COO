"use client";

import { FormEvent, useMemo, useState } from "react";

import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { StatusStrip } from "@/components/layout/status-strip";
import { InlineErrorBanner } from "@/components/states/inline-error-banner";
import { RetryCard } from "@/components/states/retry-card";
import { SkeletonPanel } from "@/components/states/skeleton-panel";
import { SuccessStateCard } from "@/components/states/success-state-card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { BudgetsWorkspaceContainer } from "@/features/budgets/containers/budgets-workspace-container";
import { useBudgetVariance, useBudgets, useCreateBudget, useUpdateBudget } from "@/features/budgets/hooks";
import { canEdit } from "@/lib/auth/rbac";
import { formatMoney } from "@/lib/utils/format";
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
  const [activeTab, setActiveTab] = useState("workspace");
  const [newCategory, setNewCategory] = useState("");
  const [newType, setNewType] = useState<"EXPENSE" | "REVENUE">("EXPENSE");
  const [newAmount, setNewAmount] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [editingBudgetId, setEditingBudgetId] = useState<string | null>(null);
  const [editAmount, setEditAmount] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [lastSuccess, setLastSuccess] = useState("");

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
      setLastSuccess("Budget created successfully.");
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
      setLastSuccess("Budget version updated successfully.");
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

      <StatusStrip
        items={[
          { label: "Period", value: period, tone: "neutral" },
          { label: "Budgets", value: String(sortedBudgets.length), tone: "neutral" },
          { label: "Variance", value: formatMoney(variance.data?.totals.variance_amount), tone: "warning" },
        ]}
      />

      {budgets.isLoading || variance.isLoading ? <SkeletonPanel rows={5} /> : null}

      {budgets.error || variance.error ? (
        <div className="space-y-3">
          <InlineErrorBanner
            message={
              String(
                (budgets.error as Error | undefined)?.message
                || (variance.error as Error | undefined)?.message
                || "Unable to load budget workspace.",
              )
            }
          />
          <RetryCard
            message="Retry loading budgets and variance data."
            onRetry={() => {
              void budgets.refetch();
              void variance.refetch();
            }}
          />
        </div>
      ) : null}

      {lastSuccess ? (
        <SuccessStateCard
          title="Budget workspace updated"
          description={lastSuccess === "Budget version updated successfully." ? "Latest budget version save completed." : lastSuccess}
        />
      ) : null}

      <BudgetsWorkspaceContainer
        activeTab={activeTab}
        onTabChange={setActiveTab}
        period={period}
        editable={editable}
        varianceTotals={variance.data?.totals}
        varianceLines={variance.data?.lines ?? []}
        sortedBudgets={sortedBudgets}
        newCategory={newCategory}
        onNewCategoryChange={setNewCategory}
        newType={newType}
        onNewTypeChange={setNewType}
        newAmount={newAmount}
        onNewAmountChange={setNewAmount}
        newNotes={newNotes}
        onNewNotesChange={setNewNotes}
        onCreateBudget={onCreateBudget}
        createBudgetPending={createBudget.isPending}
        editingBudgetId={editingBudgetId}
        editAmount={editAmount}
        onEditAmountChange={setEditAmount}
        editNotes={editNotes}
        onEditNotesChange={setEditNotes}
        onSaveEdit={onSaveEdit}
        updateBudgetPending={updateBudget.isPending}
        onCancelEdit={() => {
          setEditingBudgetId(null);
          setEditAmount("");
          setEditNotes("");
        }}
        onStartEdit={(budget) => {
          setEditingBudgetId(budget.id);
          setEditAmount(budget.planned_amount);
          setEditNotes(budget.notes || "");
        }}
      />
    </div>
  );
}

