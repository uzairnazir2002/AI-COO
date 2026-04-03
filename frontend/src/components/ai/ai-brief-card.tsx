"use client";

import { AIInsightPanel } from "@/components/common/ai-insight-panel";

type AiSummary = {
  headline: string;
  highlights: string[];
  risks: string[];
  actions: string[];
  confidence: string;
};

export function AiBriefCard({
  summary,
  fallbackUsed,
}: {
  summary: AiSummary | null;
  fallbackUsed?: boolean;
}) {
  return <AIInsightPanel summary={summary} fallbackUsed={fallbackUsed} />;
}

