"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { OnboardingProgressRail } from "@/components/shell/onboarding-progress-rail";
import { Button } from "@/components/ui/button";
import { StatusStrip } from "@/components/layout/status-strip";
import { OnboardingWorkspaceContainer } from "@/features/onboarding/containers/onboarding-workspace-container";
import { useOnboardingProgress } from "@/features/onboarding/hooks";
import { useState } from "react";

export default function OnboardingPage() {
  const progress = useOnboardingProgress({ includeAlerts: true });
  const orgId = progress.orgId;
  const [activeTab, setActiveTab] = useState("checklist");

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="No organization"
        title="Create or select an organization to start onboarding."
        description="The onboarding workspace is org-scoped and tracks data readiness, forecast signal, alerts, and reporting."
        actions={[{ label: "Go to organizations", href: "/app/orgs" }]}
      />
    );
  }

  const hasTransactions = progress.hasTransactions;
  const hasReports = progress.hasReports;
  const hasForecast = progress.hasForecast;
  const hasAlerts = progress.hasAlerts;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Onboarding"
        description={`Bring ${progress.orgName || "your organization"} from empty workspace to live financial cockpit.`}
        actions={
          <Button asChild variant="outline">
            <Link href="/app/dashboard">
              Skip to dashboard <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        }
      />

      {!progress.isComplete ? (
        <OnboardingProgressRail
          orgName={progress.orgName}
          completedCount={progress.completedCount}
          totalSteps={progress.steps.length}
          progressPercent={progress.progressPercent}
          nextStep={progress.nextStep}
        />
      ) : null}

      <StatusStrip
        items={[
          { label: "Progress", value: `${progress.progressPercent}%`, tone: progress.isComplete ? "live" : "warning" },
          { label: "Completed", value: `${progress.completedCount}/${progress.steps.length}`, tone: "neutral" },
          { label: "Next", value: progress.nextStep?.title || "Done", tone: "neutral" },
        ]}
      />

      <OnboardingWorkspaceContainer
        activeTab={activeTab}
        onTabChange={setActiveTab}
        steps={progress.steps}
        hasTransactions={hasTransactions}
        hasForecast={hasForecast}
        hasAlerts={hasAlerts}
        hasReports={hasReports}
      />
    </div>
  );
}

