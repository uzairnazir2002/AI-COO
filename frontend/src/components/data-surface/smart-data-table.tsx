"use client";

import { RightRail } from "@/components/layout/right-rail";
import { cn } from "@/lib/utils/cn";

export function SmartDataTable({
  title,
  description,
  toolbar,
  table,
  side,
  className,
}: {
  title: string;
  description?: string;
  toolbar?: React.ReactNode;
  table: React.ReactNode;
  side?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("grid gap-4 xl:grid-cols-[1.4fr_0.6fr]", className)}>
      <div className="space-y-3">
        <div className="space-y-1">
          <h2 className="text-base font-semibold">{title}</h2>
          {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
        </div>
        {toolbar}
        {table}
      </div>
      {side ? <RightRail>{side}</RightRail> : null}
    </section>
  );
}
