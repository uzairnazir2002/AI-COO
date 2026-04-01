"use client";

import type { FormEvent } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { TabNav } from "@/components/layout/tab-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PlannedVsActualChartPanel } from "@/features/budgets/panels/planned-vs-actual-chart-panel";
import { VersionComparePanel } from "@/features/budgets/panels/version-compare-panel";
import { formatMoney, formatPercent } from "@/lib/utils/format";
import type { Budget, BudgetVariance } from "@/types/domain";

type BudgetFilter = "ALL" | "EXPENSE" | "REVENUE";

export function BudgetsWorkspaceContainer({
  activeTab,
  onTabChange,
  period,
  editable,
  varianceTotals,
  varianceLines,
  sortedBudgets,
  newCategory,
  onNewCategoryChange,
  newType,
  onNewTypeChange,
  newAmount,
  onNewAmountChange,
  newNotes,
  onNewNotesChange,
  onCreateBudget,
  createBudgetPending,
  editingBudgetId,
  editAmount,
  onEditAmountChange,
  editNotes,
  onEditNotesChange,
  onSaveEdit,
  updateBudgetPending,
  onCancelEdit,
  onStartEdit,
}: {
  activeTab: string;
  onTabChange: (tab: string) => void;
  period: string;
  editable: boolean;
  varianceTotals?: BudgetVariance["totals"];
  varianceLines: BudgetVariance["lines"];
  sortedBudgets: Budget[];
  newCategory: string;
  onNewCategoryChange: (value: string) => void;
  newType: "EXPENSE" | "REVENUE";
  onNewTypeChange: (value: "EXPENSE" | "REVENUE") => void;
  newAmount: string;
  onNewAmountChange: (value: string) => void;
  newNotes: string;
  onNewNotesChange: (value: string) => void;
  onCreateBudget: (event: FormEvent<HTMLFormElement>) => void;
  createBudgetPending: boolean;
  editingBudgetId: string | null;
  editAmount: string;
  onEditAmountChange: (value: string) => void;
  editNotes: string;
  onEditNotesChange: (value: string) => void;
  onSaveEdit: () => Promise<void>;
  updateBudgetPending: boolean;
  onCancelEdit: () => void;
  onStartEdit: (budget: Budget) => void;
}) {
  return (
    <>
      <TabNav
        active={activeTab}
        onChange={onTabChange}
        items={[
          { id: "workspace", label: "Workspace" },
          { id: "variance", label: "Variance" },
        ]}
      />

      {activeTab === "workspace" ? (
        <section className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
            <Panel>
              <PanelHeader>
                <h2 className="text-base font-semibold">Variance summary</h2>
              </PanelHeader>
              <PanelBody className="space-y-2">
                <p className="text-sm text-muted-foreground">Period: {period}</p>
                <div className="grid gap-2 md:grid-cols-3">
                  <div className="rounded-2xl border border-border/70 bg-card/70 p-3">
                    <p className="text-xs text-muted-foreground">Planned</p>
                    <p className="text-lg font-semibold">{formatMoney(varianceTotals?.planned_amount)}</p>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-card/70 p-3">
                    <p className="text-xs text-muted-foreground">Actual</p>
                    <p className="text-lg font-semibold">{formatMoney(varianceTotals?.actual_amount)}</p>
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-card/70 p-3">
                    <p className="text-xs text-muted-foreground">Variance</p>
                    <p className="text-lg font-semibold">{formatMoney(varianceTotals?.variance_amount)}</p>
                  </div>
                </div>
              </PanelBody>
            </Panel>

            <Panel>
              <PanelHeader>
                <h2 className="text-base font-semibold">Create budget</h2>
              </PanelHeader>
              <PanelBody>
                {!editable ? (
                  <p className="text-sm text-muted-foreground">Read-only for viewers.</p>
                ) : (
                  <form className="grid gap-2 md:grid-cols-2" onSubmit={onCreateBudget}>
                    <Input
                      placeholder="Category (e.g. Ops)"
                      value={newCategory}
                      onChange={(event) => onNewCategoryChange(event.target.value)}
                    />
                    <Select value={newType} onValueChange={(value) => onNewTypeChange(value as "EXPENSE" | "REVENUE")}>
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
                      onChange={(event) => onNewAmountChange(event.target.value)}
                    />
                    <Input
                      placeholder="Notes (optional)"
                      value={newNotes}
                      onChange={(event) => onNewNotesChange(event.target.value)}
                    />
                    <div className="md:col-span-2">
                      <Button type="submit" disabled={createBudgetPending}>
                        Save budget
                      </Button>
                    </div>
                  </form>
                )}
              </PanelBody>
            </Panel>
          </div>

          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Current budgets</h2>
            </PanelHeader>
            <PanelBody>
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
                                    onChange={(event) => onEditAmountChange(event.target.value)}
                                  />
                                  <Input
                                    className="w-[180px]"
                                    placeholder="Notes"
                                    value={editNotes}
                                    onChange={(event) => onEditNotesChange(event.target.value)}
                                  />
                                  <Button size="sm" onClick={() => void onSaveEdit()} disabled={updateBudgetPending}>Save</Button>
                                  <Button size="sm" variant="ghost" onClick={onCancelEdit}>Cancel</Button>
                                </div>
                              ) : (
                                <Button size="sm" variant="outline" onClick={() => onStartEdit(budget)}>
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
            </PanelBody>
          </Panel>

          <VersionComparePanel budgets={sortedBudgets} />
          <PlannedVsActualChartPanel lines={varianceLines} />
        </section>
      ) : null}

      {activeTab === "variance" ? (
        <section className="space-y-4">
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Variance lines</h2>
            </PanelHeader>
            <PanelBody>
              {varianceLines.length === 0 ? (
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
                      {varianceLines.map((line) => (
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
            </PanelBody>
          </Panel>
        </section>
      ) : null}
    </>
  );
}
