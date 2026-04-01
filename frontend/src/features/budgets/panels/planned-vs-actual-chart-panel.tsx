"use client";

import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";

import { ChartCanvas } from "@/components/charts/chart-canvas";
import { ChartCard } from "@/components/charts/chart-card";
import { ChartFrame } from "@/components/charts/chart-frame";
import { FinancialTooltip } from "@/components/charts/chart-tooltip";
import { chartPalette } from "@/components/charts/theme";
import { EmptyState } from "@/components/common/empty-state";
import { formatCompactMoney } from "@/lib/utils/format";
import type { BudgetVariance } from "@/types/domain";

type VarianceLine = BudgetVariance["lines"][number];

export function PlannedVsActualChartPanel({ lines }: { lines: VarianceLine[] }) {
  const data = lines.map((line) => ({
    category: line.category,
    planned: Number(line.planned_amount),
    actual: Number(line.actual_amount),
  }));

  return (
    <ChartCard
      title="Planned vs actual"
      description="Category-level budget baseline compared to recorded actuals for the current period."
      empty={
        data.length === 0 ? (
          <EmptyState
            eyebrow="No chart data"
            title="Add budget rows to render planned vs actual trend."
            description="This chart appears once variance lines are available."
          />
        ) : undefined
      }
    >
      <ChartFrame className="h-80 w-full" label="Planned vs actual chart" description="Bar chart by category for planned and actual values.">
        <ChartCanvas className="h-80 w-full">
          {({ width, height }) => (
            <BarChart width={width} height={height} data={data}>
              <CartesianGrid stroke={chartPalette.grid} strokeDasharray="3 3" />
              <XAxis dataKey="category" />
              <YAxis tickFormatter={(v) => formatCompactMoney(v)} />
              <Tooltip content={<FinancialTooltip />} />
              <Legend />
              <Bar dataKey="planned" name="Planned" fill={chartPalette.revenueStroke} radius={[6, 6, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="actual" name="Actual" fill={chartPalette.expenseStroke} radius={[6, 6, 0, 0]} isAnimationActive={false} />
            </BarChart>
          )}
        </ChartCanvas>
      </ChartFrame>
    </ChartCard>
  );
}
