"use client";

import { useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Line, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowRight, BellRing, Download } from "lucide-react";

import { AIInsightPanel } from "@/components/common/ai-insight-panel";
import { AlertCard } from "@/components/common/alert-card";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SectionHeader } from "@/components/common/section-header";
import { ChartCard } from "@/components/charts/chart-card";
import { ChartCanvas } from "@/components/charts/chart-canvas";
import { ChartFrame } from "@/components/charts/chart-frame";
import { chartPalette } from "@/components/charts/theme";
import { FinancialTooltip } from "@/components/charts/chart-tooltip";
import { KpiCard } from "@/components/kpi/kpi-card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useDashboardData } from "@/features/dashboard/hooks";
import { computeChartDomain, downsamplePoints, toNumber } from "@/lib/utils/chart";
import { formatCompactMoney, formatMoney, shiftDaysISO, todayISO } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";

export function DashboardPageClient() {
  const data = useDashboardData();
  const [activeAlertId, setActiveAlertId] = useState<string | null>(null);
  const cashflowGranularity = useAppStore((s) => s.cashflowGranularity);
  const setCashflowGranularity = useAppStore((s) => s.setCashflowGranularity);
  const setGlobalDateRange = useAppStore((s) => s.setGlobalDateRange);

  if (!data.orgId) {
    return (
      <EmptyState
        eyebrow="No organization"
        title="Select or create an organization to continue."
        description="The dashboard is fully org-scoped. Once an organization is selected, analytics, reports, and permissions all follow that context."
        actions={[{ label: "Go to organizations", href: "/app/orgs" }]}
      />
    );
  }

  if (data.error) {
    return <ErrorState description={String((data.error as Error).message || data.error)} />;
  }

  const pointsRaw =
    data.cashflow?.points.map((p) => ({
      ...p,
      revenue: toNumber(p.revenue),
      expense: toNumber(p.expense),
      net: toNumber(p.net),
    })) || [];
  const points = downsamplePoints(pointsRaw, 120);
  const sparklineData = downsamplePoints(
    points.map((point) => ({ label: point.date, value: point.net })),
    40,
  );
  const burnSpark = downsamplePoints(
    points.map((point) => ({ label: point.date, value: point.expense - point.revenue })),
    40,
  );

  const hasData = points.length > 0;
  const resetToLast90Days = () => {
    const to = todayISO();
    const from = shiftDaysISO(to, -89);
    setGlobalDateRange({ from, to });
  };
  const alertDetail = data.alerts.find((item) => item.id === activeAlertId) ?? null;
  const maxImpact = data.alerts.reduce((acc, alert) => {
    const value = toNumber((alert.meta as Record<string, unknown> | undefined)?.impact);
    return Math.max(acc, Math.abs(value));
  }, 0);
  const netChange = points.length > 1 ? points[points.length - 1].net - points[0].net : 0;
  const cashflowDomain = computeChartDomain(
    points.flatMap((point) => [point.revenue, point.expense, point.net]),
    500,
  );

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Executive dashboard"
        description="KPIs, risk signals, cashflow movement, and AI narrative for the currently selected organization and date range."
        actions={
          <>
            <div className="w-36">
              <Select
                value={cashflowGranularity}
                onValueChange={(value) => setCashflowGranularity(value as "day" | "week" | "month")}
              >
                <SelectTrigger className="h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="day">Daily</SelectItem>
                  <SelectItem value="week">Weekly</SelectItem>
                  <SelectItem value="month">Monthly</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button asChild variant="outline">
              <Link href="/app/reports">
                Weekly report <Download className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild>
              <Link href="/app/transactions">
                Add transaction <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Cash balance"
          value={formatMoney(data.summary?.cash_balance)}
          hint={`${data.from} to ${data.to}`}
          sparklineData={sparklineData}
        />
        <KpiCard
          label="Runway"
          value={`${data.runway?.runway_days ?? 0} days`}
          warning={Boolean(data.runway?.alert)}
          hint={data.runway?.alert ? "Below alert threshold" : "Healthy runway buffer"}
          sparklineData={sparklineData}
        />
        <KpiCard
          label="Monthly burn"
          value={formatCompactMoney(data.summary?.burn_rate_monthly)}
          hint="Rolling burn estimate"
          sparklineData={burnSpark}
        />
        <KpiCard
          label="Net change"
          value={formatCompactMoney(netChange)}
          hint={netChange >= 0 ? "Cashflow improving" : "Cashflow under pressure"}
          sparklineData={sparklineData}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard
          title="Cashflow"
          description={`Revenue, expenses, and net (${cashflowGranularity})`}
          loading={data.loading}
          empty={
            !hasData ? (
              <EmptyState
                eyebrow="No cashflow yet"
                title="No points in selected range."
                description="This usually means your current date range has no transactions. Try widening the range or import data."
                actions={[
                  { label: "Last 90 days", onClick: resetToLast90Days, variant: "outline" },
                  { label: "Go to transactions", href: "/app/transactions" },
                ]}
              />
            ) : undefined
          }
        >
          <ChartFrame
            className="h-80 w-full"
            label="Cashflow chart"
            description={`Time series with revenue, expense, and net values in ${cashflowGranularity} intervals from ${data.from} to ${data.to}.`}
          >
            <ChartCanvas className="h-80 w-full">
              {({ width, height }) => (
                <AreaChart width={width} height={height} data={points}>
                <CartesianGrid stroke={chartPalette.grid} strokeDasharray="3 3" />
                <XAxis dataKey="date" tickLine={false} />
                <YAxis domain={cashflowDomain} tickFormatter={(v) => formatCompactMoney(v)} />
                <Tooltip content={<FinancialTooltip />} />
                <Area dataKey="revenue" name="Revenue" stroke={chartPalette.revenueStroke} fill={chartPalette.revenueFill} fillOpacity={0.35} isAnimationActive={false} />
                <Area dataKey="expense" name="Expense" stroke={chartPalette.expenseStroke} fill={chartPalette.expenseFill} fillOpacity={0.3} isAnimationActive={false} />
                <Line
                  type="monotone"
                  dataKey="net"
                  name="Net"
                  stroke={chartPalette.netStroke}
                  strokeWidth={2.5}
                  dot={points.length <= 2}
                  isAnimationActive={false}
                />
                </AreaChart>
              )}
            </ChartCanvas>
          </ChartFrame>
        </ChartCard>

        <ChartCard
          title="Revenue vs Expense"
          description="Comparative trend with net baseline"
          loading={data.loading}
          empty={
            !hasData ? (
              <EmptyState
                eyebrow="No trend yet"
                title="Not enough data to render trend."
                description="Load recent history to render this chart."
                actions={[{ label: "Last 90 days", onClick: resetToLast90Days, variant: "outline" }]}
              />
            ) : undefined
          }
        >
          <ChartFrame
            className="h-80 w-full"
            label="Revenue versus expense bar chart"
            description={`Grouped bars showing revenue and expense over ${cashflowGranularity} intervals from ${data.from} to ${data.to}.`}
          >
            <ChartCanvas className="h-80 w-full">
              {({ width, height }) => (
                <BarChart width={width} height={height} data={points}>
                <CartesianGrid stroke={chartPalette.grid} strokeDasharray="3 3" />
                <XAxis dataKey="date" tickLine={false} />
                <YAxis domain={cashflowDomain} tickFormatter={(v) => formatCompactMoney(v)} />
                <Tooltip content={<FinancialTooltip />} />
                <ReferenceLine y={0} stroke={chartPalette.baseline} />
                <Bar dataKey="revenue" name="Revenue" fill={chartPalette.revenueStroke} radius={[6, 6, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="expense" name="Expense" fill={chartPalette.expenseStroke} radius={[6, 6, 0, 0]} isAnimationActive={false} />
                </BarChart>
              )}
            </ChartCanvas>
          </ChartFrame>
        </ChartCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Open alerts</h2>
            <Button asChild variant="ghost">
              <Link href="/app/alerts">View all</Link>
            </Button>
          </div>
          {!data.loading && data.alerts.length === 0 ? (
            <EmptyState eyebrow="All clear" title="No open alerts." description="Current monitoring did not detect active anomalies or leak signals." />
          ) : null}
          {data.alerts.map((alert) => (
            <button key={alert.id} type="button" className="block w-full text-left" onClick={() => setActiveAlertId(alert.id)}>
              <AlertCard alert={alert} maxImpact={maxImpact} />
            </button>
          ))}
        </section>

        <AIInsightPanel summary={data.ai?.summary_json ?? null} fallbackUsed={data.ai?.fallback_used} />
      </div>

      <AnimatePresence>
        {alertDetail ? (
          <>
            <motion.button
              type="button"
              className="fixed inset-0 z-40 bg-background/55 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setActiveAlertId(null)}
              aria-label="Close alert drawer"
            />
            <motion.aside
              initial={{ x: 420 }}
              animate={{ x: 0 }}
              exit={{ x: 420 }}
              className="fixed right-0 top-0 z-50 h-full w-full max-w-xl border-l border-border bg-background p-6 shadow-2xl"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Alert detail</p>
                  <h2 className="mt-2 text-2xl font-semibold">{alertDetail.title}</h2>
                </div>
                <Button variant="ghost" onClick={() => setActiveAlertId(null)}>
                  Close
                </Button>
              </div>
              <div className="mt-6 rounded-[24px] border border-border/70 bg-card/75 p-5">
                <p className="text-sm text-muted-foreground">{alertDetail.description}</p>
                <pre className="mt-4 overflow-auto rounded-2xl bg-muted p-4 text-xs">{JSON.stringify(alertDetail.meta ?? {}, null, 2)}</pre>
              </div>
            </motion.aside>
          </>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
