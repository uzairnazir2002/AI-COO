"use client";

import { Line, LineChart } from "recharts";

import { downsamplePoints } from "@/lib/utils/chart";
import { ChartCanvas } from "@/components/charts/chart-canvas";
import { ChartFrame } from "@/components/charts/chart-frame";

export function Sparkline({
  data,
  dataKey,
  color = "hsl(var(--primary))",
  ariaLabel = "KPI trend sparkline",
}: {
  data: Array<Record<string, number | string>>;
  dataKey: string;
  color?: string;
  ariaLabel?: string;
}) {
  const points = downsamplePoints(data, 40);
  if (points.length < 2) return null;
  return (
    <ChartFrame className="h-10 w-full" label={ariaLabel} description={`${ariaLabel}. Small trend line without axis labels.`}>
      <ChartCanvas className="h-10 w-full">
        {({ width, height }) => (
          <LineChart width={width} height={height} data={points}>
          <Line type="monotone" dataKey={dataKey} stroke={color} dot={false} strokeWidth={2} />
          </LineChart>
        )}
      </ChartCanvas>
    </ChartFrame>
  );
}
