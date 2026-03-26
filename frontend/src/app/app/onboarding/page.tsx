"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, FileText, Rocket, Wallet } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useOnboardingProgress } from "@/features/onboarding/hooks";
import { useAppStore } from "@/store/appStore";

export default function OnboardingPage() {
  const progress = useOnboardingProgress({ includeAlerts: true });
  const orgId = progress.orgId;

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

  const iconByStep = {
    transactions: Wallet,
    signal: Rocket,
    reports: FileText,
  } as const;

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

      <Card>
        <CardHeader>
          <CardTitle>Readiness snapshot</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <StatusTile label="Transactions" value={hasTransactions ? "Ready" : "Pending"} done={hasTransactions} />
          <StatusTile label="Forecast" value={hasForecast ? "Ready" : "Pending"} done={hasForecast} />
          <StatusTile label="Alerts" value={hasAlerts ? "Live" : "Quiet"} done={hasAlerts} />
          <StatusTile label="Reports" value={hasReports ? "Ready" : "Pending"} done={hasReports} />
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-3">
        {progress.steps.map((step) => {
          const Icon = iconByStep[step.key];
          return (
          <Card key={step.key}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="rounded-2xl bg-primary/10 p-3 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <Badge variant={step.done ? "success" : "secondary"}>{step.done ? "Complete" : "Next step"}</Badge>
              </div>
              <CardTitle className="mt-4">{step.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm leading-6 text-muted-foreground">{step.description}</p>
              <Button asChild className="w-full" variant={step.done ? "outline" : "default"}>
                <Link href={step.href}>
                  {step.cta} <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>
          );
        })}
      </div>
    </div>
  );
}

function StatusTile({ label, value, done }: { label: string; value: string; done: boolean }) {
  return (
    <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase text-muted-foreground">{label}</p>
        {done ? <CheckCircle2 className="h-4 w-4 text-success" /> : null}
      </div>
      <p className="mt-3 text-xl font-semibold">{value}</p>
    </div>
  );
}
