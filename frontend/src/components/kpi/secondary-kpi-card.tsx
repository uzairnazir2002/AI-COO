"use client";

import { KpiCard } from "@/components/kpi/kpi-card";

export function SecondaryKpiCard(props: React.ComponentProps<typeof KpiCard>) {
  return <KpiCard {...props} className={["border-border/60", props.className].filter(Boolean).join(" ")} />;
}

