import { Cell, Pie, PieChart, Tooltip } from "recharts";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { ChartCanvas } from "@/components/charts/chart-canvas";
import { ChartFrame } from "@/components/charts/chart-frame";
import { formatMoney } from "@/lib/utils/format";

type CategoryRow = { category: string; value: number };

export function CategoryBreakdownPanel({
  categoryBreakdown,
  categoryColors,
  onSelect,
}: {
  categoryBreakdown: CategoryRow[];
  categoryColors: readonly string[];
  onSelect: (category: string) => void;
}) {
  return (
    <Panel>
      <PanelHeader><h2 className="text-base font-semibold">Category spend breakdown</h2></PanelHeader>
      <PanelBody className="space-y-3">
        {categoryBreakdown.length === 0 ? (
          <p className="text-sm text-muted-foreground">No expense data in current filtered result set.</p>
        ) : (
          <>
            <ChartFrame
              className="h-56"
              label="Category spend breakdown chart"
              description="Donut chart showing expense distribution by category based on current filtered transaction results."
            >
              <ChartCanvas className="h-56 w-full">
                {({ width, height }) => {
                  const radiusBase = Math.max(40, Math.min(width, height) / 2 - 12);
                  return (
                    <PieChart width={width} height={height}>
                      <Pie
                        data={categoryBreakdown}
                        dataKey="value"
                        nameKey="category"
                        cx="50%"
                        cy="50%"
                        innerRadius={Math.max(28, radiusBase * 0.6)}
                        outerRadius={Math.max(40, radiusBase)}
                        paddingAngle={2}
                        onClick={(entry) => {
                          if (!entry?.category) return;
                          onSelect(String(entry.category));
                        }}
                      >
                        {categoryBreakdown.map((row, idx) => (
                          <Cell key={row.category} fill={categoryColors[idx % categoryColors.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number) => formatMoney(v)} />
                    </PieChart>
                  );
                }}
              </ChartCanvas>
            </ChartFrame>
            <div className="space-y-2">
              {categoryBreakdown.map((row, idx) => (
                <button
                  key={row.category}
                  type="button"
                  className="flex w-full items-center justify-between rounded-xl border border-border/60 px-3 py-2 text-sm transition hover:bg-muted"
                  onClick={() => onSelect(row.category === "Other" ? "" : row.category)}
                >
                  <span className="flex items-center gap-2">
                    <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: categoryColors[idx % categoryColors.length] }} />
                    {row.category}
                  </span>
                  <span className="tabular-nums text-muted-foreground">{formatMoney(row.value)}</span>
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">Based on current filtered results.</p>
          </>
        )}
      </PanelBody>
    </Panel>
  );
}

