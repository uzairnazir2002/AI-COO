"use client";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { Skeleton } from "@/components/ui/skeleton";

export function SkeletonPanel({
  titleWidthClass = "w-40",
  rows = 4,
}: {
  titleWidthClass?: string;
  rows?: number;
}) {
  return (
    <Panel>
      <PanelHeader>
        <Skeleton className={`h-5 ${titleWidthClass}`} />
      </PanelHeader>
      <PanelBody className="space-y-3">
        {Array.from({ length: rows }).map((_, idx) => (
          <Skeleton key={idx} className="h-10 w-full" />
        ))}
      </PanelBody>
    </Panel>
  );
}

