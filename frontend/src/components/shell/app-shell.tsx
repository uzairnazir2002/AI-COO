"use client";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Activity as ActivityIcon,
  AlertTriangle,
  BarChart3,
  Boxes,
  Building2,
  ChevronsLeftRightEllipsis,
  FileText,
  Landmark,
  LineChart,
  MessageSquare,
  PiggyBank,
  Settings2,
  Sparkles,
  Wallet,
} from "lucide-react";

import { StatusStrip, type StatusItem } from "@/components/layout/status-strip";
import { PageContainer } from "@/components/layout/page-container";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { CommandPalette } from "@/components/shell/command-palette";
import { DateRangeControl } from "@/components/shell/date-range-control";
import { NotificationCenter } from "@/components/shell/notification-center";
import { OnboardingProgressRail } from "@/components/shell/onboarding-progress-rail";
import { ProfileMenu } from "@/components/shell/profile-menu";
import { QuickCreateMenu } from "@/components/shell/quick-create-menu";
import { ThemeToggle } from "@/components/common/theme-toggle";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useLocations } from "@/features/locations/hooks";
import { useOnboardingProgress } from "@/features/onboarding/hooks";
import { useOrgEventFeed } from "@/features/notifications/hooks";
import { logout } from "@/lib/api/client";
import { cn } from "@/lib/utils/cn";
import { useAppStore } from "@/store/appStore";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
};

type NavSection = {
  title: string;
  items: NavItem[];
};

const navSections: NavSection[] = [
  {
    title: "Core",
    items: [
      { href: "/app/dashboard", label: "Overview", icon: BarChart3 },
      { href: "/app/transactions", label: "Money", icon: Wallet },
      { href: "/app/budgets", label: "Budgets", icon: PiggyBank },
      { href: "/app/forecast", label: "Forecasting", icon: LineChart },
      { href: "/app/reports", label: "Reports", icon: FileText },
    ],
  },
  {
    title: "Intelligence",
    items: [
      { href: "/app/alerts", label: "Alerts", icon: AlertTriangle },
      { href: "/app/assistant", label: "AI Assistant", icon: MessageSquare },
    ],
  },
  {
    title: "Operations",
    items: [
      { href: "/app/inventory", label: "Inventory", icon: Boxes },
      { href: "/app/activity", label: "Activity", icon: ActivityIcon },
    ],
  },
  {
    title: "Admin",
    items: [
      { href: "/app/settings", label: "Settings", icon: Settings2 },
      { href: "/app/orgs", label: "Organizations", icon: Building2 },
      { href: "/app/onboarding", label: "Onboarding", icon: Sparkles },
    ],
  },
];

function streamStatusValue(value: "idle" | "connecting" | "live" | "error" | "fallback_polling") {
  if (value === "fallback_polling") return "fallback polling";
  return value;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const orgs = useAppStore((s) => s.orgs);
  const selectedOrgId = useAppStore((s) => s.selectedOrgId);
  const selectedLocationId = useAppStore((s) => s.selectedLocationId);
  const setSelectedOrgId = useAppStore((s) => s.setSelectedOrgId);
  const setSelectedLocationId = useAppStore((s) => s.setSelectedLocationId);
  const user = useAppStore((s) => s.user);
  const clearSession = useAppStore((s) => s.clearSession);
  const queryClient = useQueryClient();
  const collapsed = useAppStore((s) => s.shellCollapsed);
  const setCollapsed = useAppStore((s) => s.setShellCollapsed);
  const streamStatus = useOrgEventFeed();
  const locationsQuery = useLocations();
  const onboardingProgress = useOnboardingProgress();
  const showOnboardingRail =
    Boolean(onboardingProgress.orgId) && !onboardingProgress.isComplete && !pathname.startsWith("/app/onboarding");

  const selectedOrg = orgs.find((org) => org.org_id === selectedOrgId);

  useEffect(() => {
    if (!selectedOrgId || typeof document === "undefined") return;
    document.cookie = `ai_coo_selected_org=${selectedOrgId}; path=/; max-age=31536000; SameSite=Lax`;
  }, [selectedOrgId]);

  const statusItems: StatusItem[] = useMemo(() => {
    return [
      {
        label: "Stream",
        value: streamStatusValue(streamStatus),
        tone: streamStatus === "live" ? "live" : streamStatus === "fallback_polling" ? "warning" : "neutral",
      },
      {
        label: "Org scope",
        value: selectedOrg?.name || "not selected",
        tone: selectedOrg ? "neutral" : "warning",
      },
      {
        label: "Location",
        value: selectedLocationId ? "filtered" : "all",
        tone: "neutral",
      },
    ];
  }, [streamStatus, selectedLocationId, selectedOrg]);

  return (
    <div
      className="min-h-screen md:grid md:h-dvh md:overflow-hidden"
      style={{ gridTemplateColumns: collapsed ? "100px 1fr" : "300px 1fr" }}
    >
      <aside className="border-r border-border/70 bg-card/70 px-3 py-4 backdrop-blur-md md:sticky md:top-0 md:h-dvh md:overflow-y-auto">
        <div className="flex items-center justify-between px-2">
          <Link href="/app/dashboard" className={cn("flex items-center gap-3 rounded-2xl px-3 py-3", collapsed && "justify-center")}> 
            <div className="rounded-2xl bg-primary/12 p-2 text-primary">
              <Landmark className="h-5 w-5" />
            </div>
            {!collapsed ? (
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-primary">AI COO</p>
                <p className="text-xs text-muted-foreground">Executive operating system</p>
              </div>
            ) : null}
          </Link>
          <Button
            variant="ghost"
            size="icon"
            className="hidden md:inline-flex"
            onClick={() => setCollapsed(!collapsed)}
            aria-label="Toggle sidebar"
          >
            <ChevronsLeftRightEllipsis className="h-4 w-4" />
          </Button>
        </div>

        <div className="mt-6 space-y-5">
          {navSections.map((section) => (
            <div key={section.title} className="space-y-1">
              {!collapsed ? <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">{section.title}</p> : null}
              <nav className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm transition",
                        collapsed && "justify-center px-0",
                        active
                          ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground",
                      )}
                      aria-current={active ? "page" : undefined}
                    >
                      <Icon className="h-4 w-4" />
                      {!collapsed ? <span>{item.label}</span> : null}
                    </Link>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>
      </aside>

      <div className="min-w-0 md:h-dvh md:overflow-y-auto">
        <header className="sticky top-0 z-20 border-b border-border/70 bg-background/92 backdrop-blur-xl">
          <PageContainer className="flex flex-col gap-3 py-4">
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="min-w-[220px] flex-1 md:max-w-sm">
                <Select
                  value={selectedOrgId || orgs[0]?.org_id || "__none__"}
                  onValueChange={(value) => {
                    if (value === "__none__") return;
                    setSelectedOrgId(value);
                    queryClient.invalidateQueries();
                    if (typeof document !== "undefined") {
                      document.cookie = `ai_coo_selected_org=${value}; path=/; max-age=31536000; SameSite=Lax`;
                    }
                    router.refresh();
                  }}
                >
                  <SelectTrigger aria-label="Organization switcher" className="h-11 rounded-2xl bg-card/85">
                    <SelectValue placeholder="Select organization" />
                  </SelectTrigger>
                  <SelectContent>
                    {orgs.length === 0 ? <SelectItem value="__none__">No organizations</SelectItem> : null}
                    {orgs.map((org) => (
                      <SelectItem key={org.org_id} value={org.org_id}>
                        {org.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="min-w-[200px] md:max-w-xs">
                <Select
                  value={selectedLocationId || "__all__"}
                  onValueChange={(value) => {
                    const next = value === "__all__" ? null : value;
                    setSelectedLocationId(next);
                    queryClient.invalidateQueries({ queryKey: ["summary"] });
                    queryClient.invalidateQueries({ queryKey: ["cashflow"] });
                    queryClient.invalidateQueries({ queryKey: ["runway"] });
                    queryClient.invalidateQueries({ queryKey: ["budgetVariance"] });
                    queryClient.invalidateQueries({ queryKey: ["reports"] });
                    queryClient.invalidateQueries({ queryKey: ["transactions"] });
                  }}
                  disabled={!selectedOrgId}
                >
                  <SelectTrigger aria-label="Location scope switcher" className="h-11 rounded-2xl bg-card/85">
                    <SelectValue placeholder="All locations" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">All locations</SelectItem>
                    {(locationsQuery.data || []).map((location) => (
                      <SelectItem key={location.id} value={location.id}>
                        {location.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <DateRangeControl />
              <div className="ml-auto flex flex-wrap items-center gap-2">
                <CommandPalette
                  onAddTransaction={() => router.push("/app/transactions?action=compose")}
                  onOpenInventory={() => router.push("/app/inventory")}
                  onImportCsv={() => router.push("/app/transactions?action=import")}
                  onGenerateReport={() => router.push("/app/reports?action=generate")}
                />
                <NotificationCenter streamStatus={streamStatus} />
                <QuickCreateMenu
                  onAddTransaction={() => router.push("/app/transactions?action=compose")}
                  onImportCsv={() => router.push("/app/transactions?action=import")}
                  onGenerateReport={() => router.push("/app/reports?action=generate")}
                />
                <ThemeToggle />
                <ProfileMenu
                  email={user?.email}
                  role={selectedOrg?.role}
                  onLogout={async () => {
                    await logout();
                    clearSession();
                    router.replace("/auth/login");
                  }}
                />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Breadcrumbs />
              <StatusStrip items={statusItems} />
            </div>
            {showOnboardingRail ? (
              <OnboardingProgressRail
                orgName={onboardingProgress.orgName}
                completedCount={onboardingProgress.completedCount}
                totalSteps={onboardingProgress.steps.length}
                progressPercent={onboardingProgress.progressPercent}
                nextStep={onboardingProgress.nextStep}
              />
            ) : null}
          </PageContainer>
        </header>
        <main>
          <PageContainer>
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="min-w-0 pb-4">
              {children}
            </motion.div>
          </PageContainer>
        </main>
      </div>
    </div>
  );
}
