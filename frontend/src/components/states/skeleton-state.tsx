"use client";

import { SkeletonPanel } from "@/components/states/skeleton-panel";

export function SkeletonState(props: React.ComponentProps<typeof SkeletonPanel>) {
  return <SkeletonPanel {...props} />;
}

