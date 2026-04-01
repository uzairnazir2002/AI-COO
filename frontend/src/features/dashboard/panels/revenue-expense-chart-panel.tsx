"use client";

import { Bar, BarChart, CartesianGrid, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";

import { ChartCanvas } from "@/components/charts/chart-canvas";
import { ChartCard } from "@/components/charts/chart-card";
import { ChartFrame } from "@/components/charts/chart-frame";
import { FinancialTooltip } from "@/components/charts/chart-tooltip";
import { chartPalette } from "@/components/charts/theme";
import { EmptyState } from "@/components/common/empty-state";
import { formatCompactMoney } from "@/lib/utils/format";

type RevenueExpensePoint = {
  date: string;
  revenue: number;
  expense: number;
};

export function RevenueExpenseChartPanel({
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
  points: RevenueExpensePoint[];
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
      title="Revenue vs Expense"
      description="Comparative trend with net baseline"
      loading={loading}
      empty={
        !hasData ? (
          <EmptyState
            eyebrow="No trend yet"
            title="Not enough data to render trend."
            description="Load recent history to render this chart."
            actions={[{ label: "Last 90 days", onClick: onResetToLast90Days, variant: "outline" }]}
          />
        ) : undefined
      }
    >
      <ChartFrame
        className="h-80 w-full"
        label="Revenue versus expense bar chart"
        description={`Grouped bars showing revenue and expense over ${cashflowGranularity} intervals from ${from} to ${to}.`}
      >
        <ChartCanvas className="h-80 w-full">
          {({ width, height }) => (
            <BarChart
              width={width}
              height={height}
              data={points}
              onClick={(state) => {
                const date = (state as { activePayload?: Array<{ payload?: RevenueExpensePoint }> } | undefined)?.activePayload?.[0]?.payload?.date;
                if (date) onPointSelect?.(date);
              }}
            >
              <CartesianGrid stroke={chartPalette.grid} strokeDasharray="3 3" />
              <XAxis dataKey="date" tickLine={false} />
              <YAxis domain={domain} tickFormatter={(v) => formatCompactMoney(v)} />
              <Tooltip content={<FinancialTooltip />} />
              <ReferenceLine y={0} stroke={chartPalette.baseline} />
              {selectedPointDate ? <ReferenceLine x={selectedPointDate} stroke={chartPalette.baseline} strokeDasharray="4 3" /> : null}
              <Bar dataKey="revenue" name="Revenue" fill={chartPalette.revenueStroke} radius={[6, 6, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="expense" name="Expense" fill={chartPalette.expenseStroke} radius={[6, 6, 0, 0]} isAnimationActive={false} />
            </BarChart>
          )}
        </ChartCanvas>
      </ChartFrame>
    </ChartCard>
  );
}
