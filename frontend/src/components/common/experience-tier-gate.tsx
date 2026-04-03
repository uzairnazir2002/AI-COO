"use client";

import type { ExperienceTier } from "@/store/appStore";
import { isTierAtLeast } from "@/lib/ux/experience";

export function ExperienceTierGate({
  currentTier,
  minTier,
  fallback = null,
  children,
}: {
  currentTier: ExperienceTier;
  minTier: ExperienceTier;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}) {
  if (!isTierAtLeast(currentTier, minTier)) return <>{fallback}</>;
  return <>{children}</>;
}

