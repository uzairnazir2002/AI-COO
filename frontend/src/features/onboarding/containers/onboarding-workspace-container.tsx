"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, FileText, Rocket, Wallet } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { TabNav } from "@/components/layout/tab-nav";
import type { OnboardingStep } from "@/features/onboarding/hooks";

const iconByStep = {
  transactions: Wallet,
  signal: Rocket,
  reports: FileText,
} as const;

export function OnboardingWorkspaceContainer({
  activeTab,
  onTabChange,
  steps,
  hasTransactions,
  hasForecast,
  hasAlerts,
  hasReports,
}: {
  activeTab: string;
  onTabChange: (value: string) => void;
  steps: OnboardingStep[];
  hasTransactions: boolean;
  hasForecast: boolean;
  hasAlerts: boolean;
  hasReports: boolean;
}) {
  return (
    <>
      <TabNav
        active={activeTab}
        onChange={onTabChange}
        items={[
          { id: "checklist", label: "Checklist" },
          { id: "milestones", label: "Milestones" },
        ]}
      />

      {activeTab === "checklist" ? (
        <section className="space-y-4">
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Readiness snapshot</h2>
            </PanelHeader>
            <PanelBody className="grid gap-4 md:grid-cols-4">
              <StatusTile label="Transactions" value={hasTransactions ? "Ready" : "Pending"} done={hasTransactions} />
              <StatusTile label="Forecast" value={hasForecast ? "Ready" : "Pending"} done={hasForecast} />
              <StatusTile label="Alerts" value={hasAlerts ? "Live" : "Quiet"} done={hasAlerts} />
              <StatusTile label="Reports" value={hasReports ? "Ready" : "Pending"} done={hasReports} />
            </PanelBody>
          </Panel>

          <div className="grid gap-4 xl:grid-cols-3">
            {steps.map((step) => {
              const Icon = iconByStep[step.key];
              return (
                <Panel key={step.key}>
                  <PanelHeader>
                    <div className="flex items-center justify-between">
                      <div className="rounded-2xl bg-primary/10 p-3 text-primary">
                        <Icon className="h-5 w-5" />
                      </div>
                      <Badge variant={step.done ? "success" : "secondary"}>{step.done ? "Complete" : "Next step"}</Badge>
                    </div>
                    <h3 className="mt-4 text-base font-semibold">{step.title}</h3>
                  </PanelHeader>
                  <PanelBody className="space-y-4">
                    <p className="text-sm leading-6 text-muted-foreground">{step.description}</p>
                    <Button asChild className="w-full" variant={step.done ? "outline" : "default"}>
                      <Link href={step.href}>
                        {step.cta} <ArrowRight className="ml-2 h-4 w-4" />
                      </Link>
                    </Button>
                  </PanelBody>
                </Panel>
              );
            })}
          </div>
        </section>
      ) : null}

      {activeTab === "milestones" ? (
        <section className="space-y-4">
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">First wins</h2>
            </PanelHeader>
            <PanelBody className="grid gap-3 md:grid-cols-3">
              <MilestoneCard
                title="First import"
                done={hasTransactions}
                description={hasTransactions ? "Transaction data is flowing and dashboards are now grounded." : "Import your first transaction file to initialize financial signal."}
                cta={hasTransactions ? "Review transactions" : "Import data"}
                href={steps.find((step) => step.key === "transactions")?.href || "/app/transactions"}
              />
              <MilestoneCard
                title="First forecast"
                done={hasForecast}
                description={hasForecast ? "Forecast scenarios are available for planning and runway checks." : "Open Forecast and save an override to complete this milestone."}
                cta={hasForecast ? "Review forecast" : "Open forecast"}
                href={steps.find((step) => step.key === "signal")?.href || "/app/forecast"}
              />
              <MilestoneCard
                title="First report"
                done={hasReports}
                description={hasReports ? "A shareable report has been generated for leadership review." : "Generate the first report to lock reporting readiness."}
                cta={hasReports ? "View reports" : "Generate report"}
                href={steps.find((step) => step.key === "reports")?.href || "/app/reports"}
              />
            </PanelBody>
          </Panel>
        </section>
      ) : null}
    </>
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

function MilestoneCard({ title, description, done, cta, href }: { title: string; description: string; done: boolean; cta: string; href: string }) {
  return (
    <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold">{title}</p>
        <Badge variant={done ? "success" : "secondary"}>{done ? "Completed" : "Pending"}</Badge>
      </div>
      <p className="mt-3 text-xs leading-5 text-muted-foreground">{description}</p>
      <Button asChild className="mt-3 w-full" size="sm" variant={done ? "outline" : "default"}>
        <Link href={href}>
          {cta} <ArrowRight className="ml-2 h-4 w-4" />
        </Link>
      </Button>
    </div>
  );
}
