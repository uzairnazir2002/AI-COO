"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { OnboardingStep } from "@/features/onboarding/hooks";

type OnboardingProgressRailProps = {
  orgName: string | null;
  completedCount: number;
  totalSteps: number;
  progressPercent: number;
  nextStep: OnboardingStep | null;
};

export function OnboardingProgressRail({
  orgName,
  completedCount,
  totalSteps,
  progressPercent,
  nextStep,
}: OnboardingProgressRailProps) {
  const remaining = Math.max(totalSteps - completedCount, 0);
  const subtitle = remaining > 0 ? `${remaining} step${remaining === 1 ? "" : "s"} left` : "Ready";

  return (
    <div
      data-testid="onboarding-progress-rail"
      className="rounded-2xl border border-primary/25 bg-primary/5 px-4 py-3"
    >
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-[220px] flex-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-primary">Guided onboarding</p>
            <Badge variant={remaining > 0 ? "warning" : "success"}>{subtitle}</Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {orgName ? `${orgName}` : "Current organization"} completion: {completedCount}/{totalSteps}
          </p>
          <p className="mt-1 text-[11px] text-muted-foreground">This guidance remains visible until all baseline onboarding steps are complete.</p>
        </div>
        {nextStep ? (
          <Button asChild size="sm" data-testid="onboarding-progress-next">
            <Link href={nextStep.href}>
              {nextStep.cta} <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        ) : (
          <span className="inline-flex items-center gap-1 text-sm font-medium text-success">
            <CheckCircle2 className="h-4 w-4" />
            Complete
          </span>
        )}
      </div>
      <div className="mt-3 h-2 rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out"
          style={{ width: `${Math.max(4, progressPercent)}%` }}
          aria-label={`Onboarding progress ${progressPercent}%`}
        />
      </div>
    </div>
  );
}

