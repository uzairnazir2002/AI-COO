"use client";

import { Area, AreaChart, CartesianGrid, Line, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";

import { ChartCanvas } from "@/components/charts/chart-canvas";
import { ChartCard } from "@/components/charts/chart-card";
import { ChartFrame } from "@/components/charts/chart-frame";
import { FinancialTooltip } from "@/components/charts/chart-tooltip";
import { chartPalette } from "@/components/charts/theme";
import { EmptyState } from "@/components/common/empty-state";
import { formatCompactMoney } from "@/lib/utils/format";

type CashflowPoint = {
  date: string;
  revenue: number;
  expense: number;
  net: number;
};

export function CashflowChartPanel({
  loading,
  hasData,
  points,
  cashflowGranularity,
  from,
  to,
  domain,
  onResetToLast90Days,
  selectedPointDate,
  onPointSelect,
}: {
  loading: boolean;
  hasData: boolean;
  points: CashflowPoint[];
  cashflowGranularity: "day" | "week" | "month";
  from: string;
  to: string;
  domain: [number, number];
  onResetToLast90Days: () => void;
  selectedPointDate?: string | null;
  onPointSelect?: (date: string) => void;
}) {
  return (
    <ChartCard
      title="Cashflow"
      description={`Revenue, expenses, and net (${cashflowGranularity})`}
      loading={loading}
      empty={
        !hasData ? (
          <EmptyState
            eyebrow="No cashflow yet"
            title="No points in selected range."
            description="This usually means your current date range has no transactions. Try widening the range or import data."
            actions={[
              { label: "Last 90 days", onClick: onResetToLast90Days, variant: "outline" },
              { label: "Go to transactions", href: "/app/transactions" },
            ]}
          />
        ) : undefined
      }
    >
      <ChartFrame
        className="h-80 w-full"
        label="Cashflow chart"
        description={`Time series with revenue, expense, and net values in ${cashflowGranularity} intervals from ${from} to ${to}.`}
      >
        <ChartCanvas className="h-80 w-full">
          {({ width, height }) => (
            <AreaChart
              width={width}
              height={height}
              data={points}
              onClick={(state) => {
                const date = (state as { activePayload?: Array<{ payload?: CashflowPoint }> } | undefined)?.activePayload?.[0]?.payload?.date;
                if (date) onPointSelect?.(date);
              }}
            >
              <CartesianGrid stroke={chartPalette.grid} strokeDasharray="3 3" />
              <XAxis dataKey="date" tickLine={false} />
              <YAxis domain={domain} tickFormatter={(v) => formatCompactMoney(v)} />
              <Tooltip content={<FinancialTooltip />} />
              {selectedPointDate ? <ReferenceLine x={selectedPointDate} stroke={chartPalette.baseline} strokeDasharray="4 3" /> : null}
              <Area
                dataKey="revenue"
                name="Revenue"
                stroke={chartPalette.revenueStroke}
                fill={chartPalette.revenueFill}
                fillOpacity={0.35}
                isAnimationActive={false}
              />
              <Area
                dataKey="expense"
                name="Expense"
                stroke={chartPalette.expenseStroke}
                fill={chartPalette.expenseFill}
                fillOpacity={0.3}
                isAnimationActive={false}
              />
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
  );
}
