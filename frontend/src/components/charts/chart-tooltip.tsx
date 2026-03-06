"use client";

import type { NameType, ValueType } from "recharts/types/component/DefaultTooltipContent";
import type { TooltipProps } from "recharts";

import { formatMoney } from "@/lib/utils/format";

type FormatterMap = Record<string, (value: number) => string>;

export function FinancialTooltip({
  active,
  payload,
  label,
  valueFormatters = {},
}: TooltipProps<ValueType, NameType> & { valueFormatters?: FormatterMap }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="min-w-48 rounded-2xl border border-border bg-popover/95 p-3 text-xs shadow-xl backdrop-blur">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{String(label)}</p>
      <div className="space-y-1.5">
        {payload.map((entry) => {
          const key = String(entry.dataKey || entry.name || "value");
          const formatter = valueFormatters[key];
          const value = Number(entry.value ?? 0);
          return (
            <div key={key} className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2">
                <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: entry.color || "currentColor" }} />
                <span className="text-foreground/85">{String(entry.name || key)}</span>
              </span>
              <span className="font-medium tabular-nums">{formatter ? formatter(value) : formatMoney(value)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
