"use client";

import { cn } from "@/lib/utils/cn";

type WizardStep = {
  id: string;
  label: string;
  description?: string;
};

export function WizardStepper({
  steps,
  currentStep,
  className,
}: {
  steps: WizardStep[];
  currentStep: number;
  className?: string;
}) {
  return (
    <ol className={cn("grid gap-2 sm:grid-cols-4", className)}>
      {steps.map((step, index) => {
        const stepNumber = index + 1;
        const active = currentStep === stepNumber;
        const complete = currentStep > stepNumber;
        return (
          <li
            key={step.id}
            className={cn(
              "rounded-xl border px-3 py-2",
              complete || active ? "border-primary/40 bg-primary/10 text-foreground" : "border-border/60 text-muted-foreground",
            )}
            aria-current={active ? "step" : undefined}
          >
            <p className="text-xs font-medium">
              {stepNumber}. {step.label}
            </p>
            {step.description ? <p className="mt-1 text-[11px]">{step.description}</p> : null}
          </li>
        );
      })}
    </ol>
  );
}

