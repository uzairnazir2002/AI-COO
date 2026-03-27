"use client";

import { useMemo } from "react";

import { useAlerts } from "@/features/alerts/hooks";
import { useForecast } from "@/features/forecast/hooks";
import { useReports } from "@/features/reports/hooks";
import { useTransactions } from "@/features/transactions/hooks";
import { useAppStore } from "@/store/appStore";

export type OnboardingStep = {
  key: "transactions" | "signal" | "reports";
  title: string;
  description: string;
  href: string;
  cta: string;
  done: boolean;
};

type OnboardingProgressOptions = {
  includeAlerts?: boolean;
};

export function useOnboardingProgress(options: OnboardingProgressOptions = {}) {
  const includeAlerts = options.includeAlerts ?? false;
  const selectedOrg = useAppStore((s) => s.orgs.find((org) => org.org_id === s.selectedOrgId));
  const orgId = selectedOrg?.org_id;

  const transactions = useTransactions({ page: 1, page_size: 1 });
  const reports = useReports();
  const forecast = useForecast(3);
  const alerts = useAlerts("open", undefined, includeAlerts);

  const hasTransactions = (transactions.data?.total ?? 0) > 0;
  const hasReports = (reports.data?.items.length ?? 0) > 0;
  const hasForecast = (forecast.data?.scenarios.base.length ?? 0) > 0;
  const hasAlerts = includeAlerts ? (alerts.data?.items.length ?? 0) > 0 : false;

  const steps: OnboardingStep[] = useMemo(
    () => [
      {
        key: "transactions",
        title: "Load operating data",
        description: "Add or import transactions so the cockpit has a source of truth.",
        href: "/app/transactions?action=import",
        cta: hasTransactions ? "Review transactions" : "Import data",
        done: hasTransactions,
      },
      {
        key: "signal",
        title: "Generate financial signal",
        description: "Forecast and alerting become useful once trend data exists.",
        href: "/app/forecast",
        cta: hasForecast || hasAlerts ? "Review forecast" : "Open forecast",
        done: hasForecast || hasAlerts,
      },
      {
        key: "reports",
        title: "Publish a weekly report",
        description: "Generate the first report so leadership can review a shareable summary.",
        href: "/app/reports?action=generate",
        cta: hasReports ? "View reports" : "Generate report",
        done: hasReports,
      },
    ],
    [hasAlerts, hasForecast, hasReports, hasTransactions],
  );

  const completedCount = steps.filter((step) => step.done).length;
  const isComplete = completedCount === steps.length;
  const nextStep = steps.find((step) => !step.done) ?? null;
  const progressPercent = Math.round((completedCount / Math.max(steps.length, 1)) * 100);

  return {
    orgId,
    orgName: selectedOrg?.name ?? null,
    hasTransactions,
    hasForecast,
    hasAlerts,
    hasReports,
    steps,
    completedCount,
    isComplete,
    nextStep,
    progressPercent,
  };
}
