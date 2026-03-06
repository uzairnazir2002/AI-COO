"use client";

import { useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceDot, Tooltip, XAxis, YAxis } from "recharts";
import { RotateCcw, Save } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { ChartCard } from "@/components/charts/chart-card";
import { ChartCanvas } from "@/components/charts/chart-canvas";
import { ChartFrame } from "@/components/charts/chart-frame";
import { chartPalette } from "@/components/charts/theme";
import { FinancialTooltip } from "@/components/charts/chart-tooltip";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useForecast, useForecastOverride } from "@/features/forecast/hooks";
import { computeChartDomain, toNumber } from "@/lib/utils/chart";
import { formatCompactMoney, formatMoney } from "@/lib/utils/format";

type DraftRow = { revenue: string; expense: string };

export default function ForecastPage() {
  const [months, setMonths] = useState<3 | 6>(6);
  const [scenario, setScenario] = useState<"base" | "high" | "low">("base");
  const [drafts, setDrafts] = useState<Record<string, DraftRow>>({});
  const [savedOverrideMonths, setSavedOverrideMonths] = useState<string[]>([]);

  const toast = useToast();
  const forecast = useForecast(months);
  const override = useForecastOverride();

  const points = useMemo(() => {
    const arr = forecast.data?.scenarios[scenario] ?? [];
    return arr.map((item) => {
      const revenue = toNumber(item.revenue_pred);
      const expense = toNumber(item.expense_pred);
      const low = toNumber(item.confidence_low);
      const high = toNumber(item.confidence_high);
      return {
        ...item,
        revenue_pred: revenue,
        expense_pred: expense,
        confidence_low: low,
        confidence_high: high,
        confidence_band: Math.max(0, high - low),
        net: revenue - expense,
      };
    });
  }, [forecast.data, scenario]);

  const runwayProjection = useMemo(() => {
    let runningCash = 0;
    return points.map((point) => {
      runningCash += point.net;
      return { month: point.month, projected_cash_delta: runningCash };
    });
  }, [points]);

  const risk = points.length > 0 && points[points.length - 1].expense_pred > points[points.length - 1].revenue_pred;
  const hasVariance = points.some((point) => Math.abs(point.revenue_pred) > 0 || Math.abs(point.expense_pred) > 0 || Math.abs(point.confidence_high - point.confidence_low) > 0);
  const forecastDomain = useMemo(
    () => computeChartDomain(points.flatMap((point) => [point.revenue_pred, point.expense_pred, point.confidence_low, point.confidence_high]), 100),
    [points],
  );
  const runwayDomain = useMemo(() => computeChartDomain(runwayProjection.map((p) => p.projected_cash_delta), 100), [runwayProjection]);

  async function saveDraft(month: string) {
    const row = drafts[month];
    if (!row) return;
    await override.mutateAsync({
      month,
      scenario: scenario.toUpperCase() as "BASE" | "HIGH" | "LOW",
      revenue_override: row.revenue.trim() ? Number(row.revenue) : undefined,
      expense_override: row.expense.trim() ? Number(row.expense) : undefined,
    });
    setSavedOverrideMonths((prev) => (prev.includes(month) ? prev : [...prev, month]));
    setDrafts((prev) => {
      const next = { ...prev };
      delete next[month];
      return next;
    });
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Forecast"
        description="Scenario planning with confidence interval band and override markers."
        actions={
          <>
            <div className="w-24">
              <Select value={String(months)} onValueChange={(value) => setMonths(Number(value) as 3 | 6)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="3">3 mo</SelectItem>
                  <SelectItem value="6">6 mo</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-32">
              <Select value={scenario} onValueChange={(value) => setScenario(value as "base" | "high" | "low")}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="base">Base</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </>
        }
      />

      {points.length === 0 ? (
        <EmptyState
          eyebrow="Not enough signal"
          title="Add at least 30 days of data to unlock forecast confidence."
          description="The backend forecast endpoint is used as-is. This view waits for enough history instead of guessing."
          actions={[{ label: "Go to transactions", href: "/app/transactions" }]}
        />
      ) : null}

      {risk ? <p className="rounded-2xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning">Projected expenses exceed revenue at the outer horizon.</p> : null}
      {!forecast.isLoading && points.length > 0 && !hasVariance ? (
        <p className="rounded-2xl border border-border/60 bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
          Forecast is currently flat at zero. Import more historical transactions to unlock meaningful projections.
        </p>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <ChartCard
          title="Scenario projection"
          description="Revenue vs expense with confidence interval band"
          loading={forecast.isLoading}
          empty={
            !forecast.isLoading && !hasVariance ? (
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

        <ChartCard
          title="Projected runway delta"
          description="Derived from forecast net cashflow (projection)"
          loading={forecast.isLoading}
          empty={
            !forecast.isLoading && !hasVariance ? (
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
      </div>

      <Card>
        <CardHeader><CardTitle>Override editor</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <p data-testid="forecast-dirty-count" className="text-sm text-muted-foreground">Dirty rows: {Object.keys(drafts).length}</p>
            <Button
              data-testid="forecast-save-all"
              variant="outline"
              disabled={Object.keys(drafts).length === 0 || override.isPending}
              onClick={async () => {
                for (const month of Object.keys(drafts)) await saveDraft(month);
                toast.toast({ title: "All overrides saved" });
              }}
            >
              <Save className="mr-2 h-4 w-4" /> Save all
            </Button>
            <Button data-testid="forecast-reset-all" variant="ghost" disabled={Object.keys(drafts).length === 0} onClick={() => setDrafts({})}>
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
                        <Input data-testid={`forecast-override-revenue-${p.month}`} value={draft.revenue} placeholder="leave empty" onChange={(e) => setDrafts((prev) => ({ ...prev, [p.month]: { ...draft, revenue: e.target.value } }))} />
                      </td>
                      <td>
                        <Input data-testid={`forecast-override-expense-${p.month}`} value={draft.expense} placeholder="leave empty" onChange={(e) => setDrafts((prev) => ({ ...prev, [p.month]: { ...draft, expense: e.target.value } }))} />
                      </td>
                      <td>{formatMoney(p.confidence_low)} - {formatMoney(p.confidence_high)}</td>
                      <td>
                        <div className="flex gap-2">
                          <Button
                            data-testid={`forecast-save-${p.month}`}
                            size="sm"
                            disabled={!isDirty || override.isPending}
                            onClick={async () => {
                              await saveDraft(p.month);
                              toast.toast({ title: `Override saved for ${p.month}` });
                            }}
                          >
                            Save
                          </Button>
                          <Button
                            data-testid={`forecast-reset-${p.month}`}
                            size="sm"
                            variant="outline"
                            disabled={!isDirty}
                            onClick={() => {
                              setDrafts((prev) => {
                                const next = { ...prev };
                                delete next[p.month];
                                return next;
                              });
                            }}
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
        </CardContent>
      </Card>
    </div>
  );
}
