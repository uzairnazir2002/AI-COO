"use client";

import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AIInsightPanel } from "@/components/common/ai-insight-panel";
import { AlertCard } from "@/components/common/alert-card";
import { ChartCard } from "@/components/charts/chart-card";
import { KpiCard } from "@/components/kpi/kpi-card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboardData } from "@/features/dashboard/hooks";
import { formatMoney } from "@/lib/utils/format";

export function DashboardPageClient() {
  const data = useDashboardData();

  if (!data.orgId) {
    return <p className="text-sm text-muted-foreground">Select an organization to continue.</p>;
  }

  if (data.loading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <Skeleton className="h-72" />
      </div>
    );
  }

  if (data.error) {
    return <p className="text-danger">{String((data.error as Error).message || data.error)}</p>;
  }

  const points = data.cashflow?.points.map((p) => ({
    ...p,
    revenue: Number(p.revenue),
    expense: Number(p.expense),
    net: Number(p.net),
  })) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="mr-auto text-2xl font-semibold">Dashboard</h1>
        <Input type="date" value={data.from} onChange={(e) => data.setFrom(e.target.value)} className="w-auto" />
        <Input type="date" value={data.to} onChange={(e) => data.setTo(e.target.value)} className="w-auto" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Cash Balance" value={formatMoney(data.summary?.cash_balance)} />
        <KpiCard label="Runway" value={`${data.runway?.runway_days ?? 0} days`} warning={Boolean(data.runway?.alert)} hint={data.runway?.alert ? "Below threshold" : undefined} />
        <KpiCard label="Burn (Monthly)" value={formatMoney(data.summary?.burn_rate_monthly)} />
        <KpiCard label="Net Profit MTD" value={formatMoney(data.summary?.net_profit_mtd)} />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard title="Cashflow" description="Revenue vs Expense">
          <div className="h-80 w-full">
            <ResponsiveContainer>
              <AreaChart data={points}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Area dataKey="revenue" stroke="#2563eb" fill="#93c5fd" fillOpacity={0.45} />
                <Area dataKey="expense" stroke="#dc2626" fill="#fca5a5" fillOpacity={0.38} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Net Trend" description="Net cash trend">
          <div className="h-80 w-full">
            <ResponsiveContainer>
              <LineChart data={points}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line dataKey="net" stroke="#0f766e" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Alerts</h2>
          {data.alerts.length === 0 ? <p className="text-sm text-muted-foreground">No open alerts.</p> : null}
          {data.alerts.map((alert) => <AlertCard key={alert.id} alert={alert} />)}
        </section>

        <AIInsightPanel summary={data.ai?.summary_json ?? null} fallbackUsed={data.ai?.fallback_used} />
      </div>
    </div>
  );
}
