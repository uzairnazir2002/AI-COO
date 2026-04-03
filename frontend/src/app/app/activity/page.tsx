"use client";

import Link from "next/link";
import { Activity, ArrowRight, Boxes, HeartPulse, ShieldCheck } from "lucide-react";

import { OperationsHealthCard } from "@/components/activity/operations-health-card";
import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { StatusStrip } from "@/components/layout/status-strip";
import { SkeletonPanel } from "@/components/states/skeleton-panel";
import { Button } from "@/components/ui/button";
import { useJobs, useRuntimeSlos, useSystemStatus } from "@/features/activity/hooks";
import { useInventoryForecast } from "@/features/inventory/hooks";
import { useAppStore } from "@/store/appStore";

export default function ActivityPage() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const role = useAppStore((s) => s.orgs.find((org) => org.org_id === s.selectedOrgId)?.role);
  const jobs = useJobs({ page: 1, page_size: 5 });
  const runtime = useRuntimeSlos();
  const systemStatus = useSystemStatus();
  const inventoryForecast = useInventoryForecast(30, 30);

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="No organization"
        title="Select an organization to view operations."
        description="Operations health is org-scoped and depends on the active organization context."
        actions={[{ label: "Go to organizations", href: "/app/orgs" }]}
      />
    );
  }

  const loading = jobs.isLoading || runtime.isLoading || systemStatus.isLoading || inventoryForecast.isLoading;
  const recentJobs = jobs.data?.items ?? [];
  const activeJobs = recentJobs.filter((job) => ["PENDING", "RUNNING", "RETRYING"].includes(job.status)).length;
  const riskRows = inventoryForecast.data?.items ?? [];
  const highRiskCount = riskRows.filter((row) => row.risk_level === "HIGH").length;
  const sloViolations = (runtime.data?.endpoints ?? []).filter((endpoint) => endpoint.breach).length;

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Operations"
        title="Activity"
        description="Essential inventory, activity, and system health in one low-noise workspace."
        scopeChips={[`Role: ${role ?? "UNKNOWN"}`, `Org: ${orgId}`]}
        actions={
          <>
            <Button asChild variant="outline">
              <Link href="/app/inventory">
                Inventory <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild>
              <Link href="/app/admin-console">
                Open admin console <ShieldCheck className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </>
        }
      />

      <StatusStrip
        items={[
          { label: "Active jobs", value: String(activeJobs), tone: activeJobs > 0 ? "warning" : "live" },
          { label: "Inventory high risk", value: String(highRiskCount), tone: highRiskCount > 0 ? "warning" : "live" },
          { label: "SLO violations", value: String(sloViolations), tone: sloViolations > 0 ? "danger" : "live" },
        ]}
      />

      {loading ? <SkeletonPanel rows={4} /> : null}

      <div className="grid gap-4 xl:grid-cols-3">
        <OperationsHealthCard title="Inventory snapshot" icon={<Boxes className="h-4 w-4 text-primary" />}>
          <p className="text-muted-foreground">Track near-term stockout risk and COGS exposure.</p>
          <p>Risk rows: {riskRows.length}</p>
          <p>High risk: {highRiskCount}</p>
          <Button asChild variant="ghost" size="sm">
            <Link href="/app/inventory">Open inventory</Link>
          </Button>
        </OperationsHealthCard>

        <OperationsHealthCard title="Activity summary" icon={<Activity className="h-4 w-4 text-primary" />}>
          <p className="text-muted-foreground">Recent background work and queue movement.</p>
          {recentJobs.length === 0 ? (
            <p>No recent jobs found.</p>
          ) : (
            <ul className="space-y-1">
              {recentJobs.slice(0, 3).map((job) => (
                <li key={job.task_id} className="rounded-xl border border-border/70 bg-card/70 px-3 py-2">
                  <span className="font-medium">{job.task_name}</span>
                  <span className="ml-2 text-xs uppercase text-muted-foreground">{job.status}</span>
                </li>
              ))}
            </ul>
          )}
          <Button asChild variant="ghost" size="sm">
            <Link href="/app/admin-console?tab=jobs">Open jobs</Link>
          </Button>
        </OperationsHealthCard>

        <OperationsHealthCard title="Health" icon={<HeartPulse className="h-4 w-4 text-primary" />}>
          <p className="text-muted-foreground">Runtime and scheduler status at a glance.</p>
          <p>Runtime endpoints monitored: {(runtime.data?.endpoints ?? []).length}</p>
          <p>Schedulers: {(systemStatus.data?.scheduler ?? []).length}</p>
          <p>SLO violations: {sloViolations}</p>
          <Button asChild variant="ghost" size="sm">
            <Link href="/app/admin-console?tab=runtime">Open runtime</Link>
          </Button>
        </OperationsHealthCard>
      </div>
    </div>
  );
}
