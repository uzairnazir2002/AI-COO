"use client";

import { Area, AreaChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceDot, Tooltip, XAxis, YAxis } from "recharts";
import { RotateCcw, Save } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { ChartCard } from "@/components/charts/chart-card";
import { ChartCanvas } from "@/components/charts/chart-canvas";
import { ChartFrame } from "@/components/charts/chart-frame";
import { FinancialTooltip } from "@/components/charts/chart-tooltip";
import { chartPalette } from "@/components/charts/theme";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { FieldHelpCallout } from "@/components/safety/field-help-callout";
import { TabNav } from "@/components/layout/tab-nav";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AssumptionsPanel, type ForecastAssumptions } from "@/features/forecast/panels/assumptions-panel";
import { RiskPanel } from "@/features/forecast/panels/risk-panel";
import { SensitivityPanel } from "@/features/forecast/panels/sensitivity-panel";
import { formatCompactMoney, formatMoney } from "@/lib/utils/format";
import type { ExperienceTier } from "@/store/appStore";

type DraftRow = { revenue: string; expense: string };

type ScenarioPoint = {
  month: string;
  revenue_pred: number;
  expense_pred: number;
  confidence_low: number;
  confidence_high: number;
  confidence_band: number;
};

type RunwayPoint = {
  month: string;
  projected_cash_delta: number;
};

export function ForecastWorkspaceContainer({
  experienceTier,
  activeTab,
  onTabChange,
  points,
  runwayProjection,
  risk,
  hasVariance,
  forecastLoading,
  months,
  scenario,
  savedOverrideMonths,
  forecastDomain,
  runwayDomain,
  drafts,
  overridePending,
  onDraftRevenueChange,
  onDraftExpenseChange,
  onSaveDraft,
  onResetDraft,
  onSaveAll,
  onResetAll,
  assumptions,
  onAssumptionsChange,
  assumptionsNetImpact,
  expenseOverRevenue,
}: {
  experienceTier: ExperienceTier;
  activeTab: string;
  onTabChange: (tab: string) => void;
  points: ScenarioPoint[];
  runwayProjection: RunwayPoint[];
  risk: boolean;
  hasVariance: boolean;
  forecastLoading: boolean;
  months: 3 | 6 | 12;
  scenario: "base" | "high" | "low";
  savedOverrideMonths: string[];
  forecastDomain: [number, number];
  runwayDomain: [number, number];
  drafts: Record<string, DraftRow>;
  overridePending: boolean;
  onDraftRevenueChange: (month: string, value: string) => void;
  onDraftExpenseChange: (month: string, value: string) => void;
  onSaveDraft: (month: string) => Promise<void>;
  onResetDraft: (month: string) => void;
  onSaveAll: () => Promise<void>;
  onResetAll: () => void;
  assumptions: ForecastAssumptions;
  onAssumptionsChange: (next: ForecastAssumptions) => void;
  assumptionsNetImpact: number;
  expenseOverRevenue: number;
}) {
  return (
    <>
      <TabNav
        active={activeTab}
        onChange={onTabChange}
        items={[
          { id: "baseline", label: "Baseline" },
          { id: "risks", label: "Risks" },
          { id: "custom", label: "Custom plan" },
        ]}
      />

      {points.length === 0 ? (
        <EmptyState
          eyebrow="Not enough signal"
          title="Add at least 30 days of data to unlock forecast confidence."
          description="The backend forecast endpoint is used as-is. This view waits for enough history instead of guessing."
          actions={[{ label: "Go to transactions", href: "/app/transactions" }]}
        />
      ) : null}

      {activeTab === "baseline" ? (
        <section className="space-y-4">
          <FieldHelpCallout
            title="Scenario guidance"
            description="Use this view to compare model confidence and projected runway impact before applying override edits."
          />
          {risk ? <p className="rounded-2xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning">Projected expenses exceed revenue at the outer horizon.</p> : null}
          {!forecastLoading && points.length > 0 && !hasVariance ? (
            <p className="rounded-2xl border border-border/60 bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
              Forecast is currently flat at zero. Import more historical transactions to unlock meaningful projections.
            </p>
          ) : null}

          <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <ChartCard
              title="Scenario projection"
              description="Revenue vs expense with confidence interval band"
              loading={forecastLoading}
              empty={
                !forecastLoading && !hasVariance ? (
                  <EmptyState
                    eyebrow="Flat baseline"
                    title="No variance to visualize yet."
                    description="Model output is currently zero across the selected horizon."
                    actions={[{ label: "Add transactions", href: "/app/transactions" }]}
                  />
                ) : undefined
              }
            >
              <ChartFrame
                className="h-80 w-full"
                label="Forecast scenario chart"
                description={`Scenario ${scenario} with revenue and expense predictions plus confidence range across ${months} months.`}
              >
                <ChartCanvas className="h-80 w-full">
                  {({ width, height }) => (
                    <ComposedChart width={width} height={height} data={points}>
                      <CartesianGrid stroke={chartPalette.grid} strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis domain={forecastDomain} tickFormatter={(v) => formatCompactMoney(v)} />
                      <Tooltip content={<FinancialTooltip />} />
                      <Legend />
                      <Area dataKey="confidence_low" name="Confidence low" stroke={chartPalette.confidenceBandStroke} fill={chartPalette.confidenceLowFill} />
                      <Area dataKey="confidence_band" name="Confidence range" stackId="confidence" stroke={chartPalette.confidenceBandStroke} fill={chartPalette.confidenceBandFill} />
                      <Line dataKey="revenue_pred" name="Revenue" stroke={chartPalette.revenueStroke} strokeWidth={2.5} dot={false} />
                      <Line dataKey="expense_pred" name="Expense" stroke={chartPalette.expenseStroke} strokeWidth={2.5} dot={false} />
                      {savedOverrideMonths.map((month) => {
                        const point = points.find((p) => p.month === month);
                        if (!point) return null;
                        return (
                          <ReferenceDot
                            key={`override-${month}`}
                            x={month}
                            y={point.revenue_pred}
                            r={4}
                            fill={chartPalette.confidenceBandStroke}
                            stroke={chartPalette.confidenceBandStroke}
                            label={{ value: "override", position: "top", fill: chartPalette.confidenceBandStroke, fontSize: 10 }}
                          />
                        );
                      })}
                    </ComposedChart>
                  )}
                </ChartCanvas>
              </ChartFrame>
            </ChartCard>
            {experienceTier === "simple" ? (
              <Panel>
                <PanelHeader><h2 className="text-base font-semibold">Quick plan controls</h2></PanelHeader>
                <PanelBody className="space-y-2 text-sm text-muted-foreground">
                  <p>Advanced assumption editing is hidden in Simple mode.</p>
                  <p>Switch to Standard or Advanced mode in Profile to edit detailed assumptions.</p>
                </PanelBody>
              </Panel>
            ) : (
              <AssumptionsPanel assumptions={assumptions} onChange={onAssumptionsChange} runwayImpactPreview={assumptionsNetImpact} />
            )}
          </div>

          <ChartCard
            title="Projected runway delta"
            description="Derived from forecast net cashflow (projection)"
            loading={forecastLoading}
            empty={
              !forecastLoading && !hasVariance ? (
                <EmptyState
                  eyebrow="No delta"
                  title="Runway projection is flat."
                  description="Projected net cashflow is zero for this horizon."
                />
              ) : undefined
            }
          >
            <ChartFrame
              className="h-80 w-full"
              label="Projected runway delta chart"
              description={`Cumulative projected cash delta for scenario ${scenario} over ${months} months.`}
            >
              <ChartCanvas className="h-80 w-full">
                {({ width, height }) => (
                  <AreaChart width={width} height={height} data={runwayProjection}>
                    <CartesianGrid stroke={chartPalette.grid} strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis domain={runwayDomain} tickFormatter={(v) => formatCompactMoney(v)} />
                    <Tooltip content={<FinancialTooltip valueFormatters={{ projected_cash_delta: (v) => formatMoney(v) }} />} />
                    <Line type="monotone" dataKey="projected_cash_delta" name="Projected cash delta" stroke={chartPalette.netStroke} strokeWidth={2.5} dot={false} />
                  </AreaChart>
                )}
              </ChartCanvas>
            </ChartFrame>
          </ChartCard>

        </section>
      ) : null}

      {activeTab === "risks" ? (
        <section className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-2">
            <RiskPanel
              risk={risk}
              lastPointMonth={points[points.length - 1]?.month ?? null}
              expenseOverRevenue={expenseOverRevenue}
            />
            <SensitivityPanel
              revenueLiftPct={Number(assumptions.revenueLiftPct || 0)}
              expenseDeltaPct={Number(assumptions.expenseDeltaPct || 0)}
              projectedNet={assumptionsNetImpact}
            />
          </div>
          <Panel>
            <PanelHeader><h2 className="text-base font-semibold">Top forecast risks</h2></PanelHeader>
            <PanelBody className="space-y-2 text-sm text-muted-foreground">
              <p>Scenario: {scenario.toUpperCase()}</p>
              <p>Horizon: {months} months</p>
              <p>Expense over revenue at horizon: {formatMoney(expenseOverRevenue)}</p>
              <p>Model confidence width: {formatMoney((points[points.length - 1]?.confidence_band ?? 0) || 0)}</p>
            </PanelBody>
          </Panel>
        </section>
      ) : null}

      {activeTab === "custom" ? (
        <section className="space-y-4">
          {experienceTier === "simple" ? (
            <Panel>
              <PanelHeader><h2 className="text-base font-semibold">Advanced assumptions are hidden in Simple mode</h2></PanelHeader>
              <PanelBody className="text-sm text-muted-foreground">
                Override editing remains available, but detailed assumption controls stay collapsed.
              </PanelBody>
            </Panel>
          ) : null}
          {experienceTier !== "simple" ? (
            <AssumptionsPanel assumptions={assumptions} onChange={onAssumptionsChange} runwayImpactPreview={assumptionsNetImpact} />
          ) : null}
          <Panel>
            <PanelHeader><h2 className="text-base font-semibold">Override editor</h2></PanelHeader>
            <PanelBody className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <p data-testid="forecast-dirty-count" className="text-sm text-muted-foreground">Dirty rows: {Object.keys(drafts).length}</p>
                <Button
                  data-testid="forecast-save-all"
                  variant="outline"
                  disabled={Object.keys(drafts).length === 0 || overridePending}
                  onClick={() => void onSaveAll()}
                >
                  <Save className="mr-2 h-4 w-4" /> Save all
                </Button>
                <Button data-testid="forecast-reset-all" variant="ghost" disabled={Object.keys(drafts).length === 0} onClick={onResetAll}>
                  <RotateCcw className="mr-2 h-4 w-4" /> Reset all
                </Button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-muted-foreground">
                      <th className="py-2">Month</th>
                      <th className="py-2">Revenue (model)</th>
                      <th className="py-2">Expense (model)</th>
                      <th className="py-2">Revenue override</th>
                      <th className="py-2">Expense override</th>
                      <th className="py-2">Confidence</th>
                      <th className="py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {points.map((p) => {
                      const draft = drafts[p.month] ?? { revenue: "", expense: "" };
                      const isDirty = Boolean(drafts[p.month]);
                      return (
                        <tr key={p.month} className="border-t">
                          <td className="py-3 font-medium">{p.month}</td>
                          <td>{formatMoney(p.revenue_pred)}</td>
                          <td>{formatMoney(p.expense_pred)}</td>
                          <td>
                              <Input
                                data-testid={`forecast-override-revenue-${p.month}`}
                                value={draft.revenue}
                                placeholder="leave empty"
                                onChange={(e) => onDraftRevenueChange(p.month, e.target.value)}
                              />
                          </td>
                          <td>
                              <Input
                                data-testid={`forecast-override-expense-${p.month}`}
                                value={draft.expense}
                                placeholder="leave empty"
                                onChange={(e) => onDraftExpenseChange(p.month, e.target.value)}
                              />
                          </td>
                          <td>{formatMoney(p.confidence_low)} - {formatMoney(p.confidence_high)}</td>
                          <td>
                            <div className="flex gap-2">
                              <Button
                                data-testid={`forecast-save-${p.month}`}
                                size="sm"
                                disabled={!isDirty || overridePending}
                                onClick={() => void onSaveDraft(p.month)}
                              >
                                Save
                              </Button>
                              <Button
                                data-testid={`forecast-reset-${p.month}`}
                                size="sm"
                                variant="outline"
                                disabled={!isDirty}
                                onClick={() => onResetDraft(p.month)}
                              >
                                Reset
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </PanelBody>
          </Panel>
        </section>
      ) : null}
    </>
  );
}
