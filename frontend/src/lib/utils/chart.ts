export type NumericSeriesPoint = {
  date?: string;
  label?: string;
  [key: string]: string | number | undefined;
};

export function downsamplePoints<T>(points: T[], maxPoints = 90): T[] {
  if (points.length <= maxPoints) return points;
  if (maxPoints < 3) return [points[0], points[points.length - 1]];
  const stride = (points.length - 1) / (maxPoints - 1);
  const sampled: T[] = [];
  for (let i = 0; i < maxPoints; i += 1) {
    const idx = Math.round(i * stride);
    sampled.push(points[idx]);
  }
  return sampled;
}

export function toNumber(value: unknown): number {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n : 0;
}

export type CategoryBreakdownRow = {
  category: string;
  value: number;
  percentage: number;
};

export function buildCategoryBreakdown(
  rows: Array<{ category?: string | null; amount?: string | number | null }>,
  maxCategories = 6,
): CategoryBreakdownRow[] {
  const buckets = new Map<string, number>();
  for (const row of rows) {
    const category = (row.category || "Uncategorized").trim() || "Uncategorized";
    const amount = Math.abs(toNumber(row.amount));
    buckets.set(category, (buckets.get(category) || 0) + amount);
  }
  const sorted = Array.from(buckets.entries())
    .map(([category, value]) => ({ category, value }))
    .sort((a, b) => b.value - a.value);
  if (sorted.length === 0) return [];
  const head = sorted.slice(0, maxCategories);
  const tail = sorted.slice(maxCategories);
  if (tail.length > 0) {
    const other = tail.reduce((acc, row) => acc + row.value, 0);
    head.push({ category: "Other", value: other });
  }
  const total = head.reduce((acc, row) => acc + row.value, 0) || 1;
  return head.map((row) => ({
    category: row.category,
    value: row.value,
    percentage: (row.value / total) * 100,
  }));
}

export function alertImpactValue(meta: Record<string, unknown> | null | undefined): number {
  if (!meta) return 0;
  return Math.max(
    Math.abs(toNumber(meta.impact)),
    Math.abs(toNumber(meta.variance_pct)),
    Math.abs(toNumber(meta.share_pct)),
  );
}

export function normalizeImpact(value: number, maxValue: number): number {
  if (!Number.isFinite(value) || value <= 0) return 0;
  if (!Number.isFinite(maxValue) || maxValue <= 0) return 0;
  return Math.max(6, Math.min(100, (value / maxValue) * 100));
}

export function computeChartDomain(values: number[], minimumSpan = 100): [number, number] {
  if (values.length === 0) return [0, minimumSpan];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    const pad = Math.max(minimumSpan / 2, Math.abs(min) * 0.15, 1);
    return [min - pad, max + pad];
  }
  const span = max - min;
  const pad = Math.max(span * 0.12, minimumSpan * 0.05, 1);
  return [min - pad, max + pad];
}
