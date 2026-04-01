"use client";

import { useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatMoney } from "@/lib/utils/format";
import type { Budget } from "@/types/domain";

export function VersionComparePanel({ budgets }: { budgets: Budget[] }) {
  const [leftId, setLeftId] = useState("");
  const [rightId, setRightId] = useState("");
  const budgetOptions = useMemo(
    () =>
      budgets.map((budget) => ({
        id: budget.id,
        label: `${budget.category} · ${budget.budget_type} · v${budget.version}`,
      })),
    [budgets],
  );
  const left = budgets.find((budget) => budget.id === leftId) ?? null;
  const right = budgets.find((budget) => budget.id === rightId) ?? null;
  const delta = left && right ? Number(right.planned_amount) - Number(left.planned_amount) : null;

  return (
    <Panel data-testid="budget-version-compare-panel">
      <PanelHeader>
        <h2 className="text-base font-semibold">Compare versions</h2>
      </PanelHeader>
      <PanelBody className="space-y-3">
        {budgets.length < 2 ? (
          <EmptyState
            eyebrow="Need more versions"
            title="Create at least two budget versions to compare."
            description="Version comparisons are available once multiple revisions exist."
          />
        ) : (
          <>
            <div className="grid gap-2 md:grid-cols-2">
              <Select value={leftId || "__none__"} onValueChange={(value) => setLeftId(value === "__none__" ? "" : value)}>
                <SelectTrigger><SelectValue placeholder="Version A" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Select version A</SelectItem>
                  {budgetOptions.map((option) => (
                    <SelectItem key={`left-${option.id}`} value={option.id}>{option.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={rightId || "__none__"} onValueChange={(value) => setRightId(value === "__none__" ? "" : value)}>
                <SelectTrigger><SelectValue placeholder="Version B" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Select version B</SelectItem>
                  {budgetOptions.map((option) => (
                    <SelectItem key={`right-${option.id}`} value={option.id}>{option.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {left && right ? (
              <div className="grid gap-2 md:grid-cols-3">
                <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                  <p className="text-xs text-muted-foreground">Version A planned</p>
                  <p className="mt-1 text-sm font-semibold">{formatMoney(left.planned_amount)}</p>
                </div>
                <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                  <p className="text-xs text-muted-foreground">Version B planned</p>
                  <p className="mt-1 text-sm font-semibold">{formatMoney(right.planned_amount)}</p>
                </div>
                <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                  <p className="text-xs text-muted-foreground">Delta (B - A)</p>
                  <p className="mt-1 text-sm font-semibold">{formatMoney(delta ?? 0)}</p>
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Pick two versions to render side-by-side comparison.</p>
            )}
          </>
        )}
      </PanelBody>
    </Panel>
  );
}
