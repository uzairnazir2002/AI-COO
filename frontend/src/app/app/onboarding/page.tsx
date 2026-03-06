"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, FileText, Rocket, Wallet } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAlerts } from "@/features/alerts/hooks";
import { useForecast } from "@/features/forecast/hooks";
import { useReports } from "@/features/reports/hooks";
import { useTransactions } from "@/features/transactions/hooks";
import { useAppStore } from "@/store/appStore";

export default function OnboardingPage() {
  const selectedOrg = useAppStore((s) => s.orgs.find((org) => org.org_id === s.selectedOrgId));
  const orgId = selectedOrg?.org_id;
  const transactions = useTransactions({ page: 1, page_size: 1 });
  const reports = useReports();
  const alerts = useAlerts("open");
  const forecast = useForecast(3);

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

  const hasTransactions = (transactions.data?.total ?? 0) > 0;
  const hasReports = (reports.data?.items.length ?? 0) > 0;
  const hasForecast = (forecast.data?.scenarios.base.length ?? 0) > 0;
  const hasAlerts = (alerts.data?.items.length ?? 0) > 0;

  const steps = [
    {
      title: "Load operating data",
      description: "Manual entry and CSV import are both active. Until you load transactions, the rest of the cockpit stays mostly empty.",
      done: hasTransactions,
      href: "/app/transactions?action=import",
      cta: hasTransactions ? "Review transactions" : "Import data",
      icon: Wallet,
    },
    {
      title: "Generate financial signal",
      description: "Forecasts, runway, and alerting become useful once the backend has enough history to compute trends.",
      done: hasForecast || hasAlerts,
      href: "/app/forecast",
      cta: hasForecast ? "Review forecast" : "Open forecast",
      icon: Rocket,
    },
    {
      title: "Publish a weekly report",
      description: "Reports are stored in object storage and stay idempotent by organization and week start.",
      done: hasReports,
      href: "/app/reports?action=generate",
      cta: hasReports ? "View reports" : "Generate report",
      icon: FileText,
    },
  ];

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Onboarding"
        description={`Bring ${selectedOrg.name} from empty workspace to live financial cockpit.`}
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
        {steps.map((step) => (
          <Card key={step.title}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="rounded-2xl bg-primary/10 p-3 text-primary">
                  <step.icon className="h-5 w-5" />
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
        ))}
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
