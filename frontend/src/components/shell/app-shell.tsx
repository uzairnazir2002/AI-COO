"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import {
  Activity as ActivityIcon,
  AlertTriangle,
  ChevronsLeftRightEllipsis,
  FileText,
  Home,
  Landmark,
  Menu,
  X,
  LineChart,
  MessageSquare,
  Settings2,
  ShieldCheck,
  Wallet,
} from "lucide-react";

import { StatusStrip, type StatusItem } from "@/components/layout/status-strip";
import { PageContainer } from "@/components/layout/page-container";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { CommandPalette } from "@/components/shell/command-palette";
import { DateRangeControl } from "@/components/shell/date-range-control";
import { NotificationCenter } from "@/components/shell/notification-center";
import { OnboardingProgressRail } from "@/components/shell/onboarding-progress-rail";
import { PrimaryNav } from "@/components/shell/primary-nav";
import { ProfileMenu } from "@/components/shell/profile-menu";
import { QuickCreateMenu } from "@/components/shell/quick-create-menu";
import { SecondaryNav } from "@/components/shell/secondary-nav";
import { TopBar } from "@/components/shell/top-bar";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useLocations } from "@/features/locations/hooks";
import { useOnboardingProgress } from "@/features/onboarding/hooks";
import { useOrgEventFeed } from "@/features/notifications/hooks";
import { logout } from "@/lib/api/client";
import { canAccessAdvancedNav } from "@/lib/ux/experience";
import { cn } from "@/lib/utils/cn";
import { useIsMdUp } from "@/lib/utils/use-is-md-up";
import { useAppStore } from "@/store/appStore";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
};

const primaryNav: NavItem[] = [
  { href: "/app/dashboard", label: "Home", icon: Home },
  { href: "/app/transactions", label: "Money", icon: Wallet },
  { href: "/app/forecast", label: "Forecast", icon: LineChart },
  { href: "/app/reports", label: "Reports", icon: FileText },
  { href: "/app/assistant", label: "AI COO", icon: MessageSquare },
];

const secondaryNav: NavItem[] = [
  { href: "/app/alerts", label: "Alerts", icon: AlertTriangle },
  { href: "/app/activity", label: "Operations", icon: ActivityIcon },
  { href: "/app/settings", label: "Settings", icon: Settings2 },
];

const advancedNav: NavItem[] = [{ href: "/app/admin-console", label: "Admin Console", icon: ShieldCheck }];

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
  const experienceTier = useAppStore((s) => s.experienceTier);
  const setExperienceTier = useAppStore((s) => s.setExperienceTier);
  const streamStatus = useOrgEventFeed();
  const locationsQuery = useLocations();
  const onboardingProgress = useOnboardingProgress();
  const showOnboardingRail =
    Boolean(onboardingProgress.orgId) && !onboardingProgress.isComplete && !pathname.startsWith("/app/onboarding");
  const reduceMotion = useReducedMotion();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const isMdUp = useIsMdUp();

  const selectedOrg = orgs.find((org) => org.org_id === selectedOrgId);
  const showAdvancedNav = canAccessAdvancedNav(selectedOrg?.role, experienceTier);
  /** When the mobile drawer is open, always show nav labels (sidebar may be icon-only when `collapsed`). */
  const navCollapsed = collapsed && !mobileNavOpen;

  useEffect(() => {
    if (!selectedOrgId || typeof document === "undefined") return;
    document.cookie = `ai_coo_selected_org=${selectedOrgId}; path=/; max-age=31536000; SameSite=Lax`;
  }, [selectedOrgId]);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

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
      {
        label: "Mode",
        value: experienceTier,
        tone: experienceTier === "advanced" ? "warning" : "neutral",
      },
    ];
  }, [streamStatus, selectedLocationId, selectedOrg, experienceTier]);

  return (
    <div
      className={cn("min-h-screen", isMdUp && "grid h-dvh overflow-hidden")}
      style={
        isMdUp ? { gridTemplateColumns: collapsed ? "100px 1fr" : "300px 1fr" } : undefined
      }
    >
      {!isMdUp ? (
        <div className="sticky top-0 z-30 flex items-center gap-2 border-b border-border/70 bg-background/95 px-3 py-2 backdrop-blur-md">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="shrink-0 rounded-xl"
            aria-label="Open navigation menu"
            aria-expanded={mobileNavOpen}
            onClick={() => setMobileNavOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <Link href="/app/dashboard" className="min-w-0 truncate text-sm font-semibold">
            AI COO
          </Link>
        </div>
      ) : null}

      {mobileNavOpen && !isMdUp ? (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-background/60 backdrop-blur-sm"
          aria-label="Close navigation menu"
          onClick={() => setMobileNavOpen(false)}
        />
      ) : null}

      <aside
        className={cn(
          "flex h-dvh flex-col border-r border-border/70 bg-card/95 px-3 py-4 backdrop-blur-md transition-transform duration-200 ease-out",
          isMdUp
            ? "static z-auto w-auto translate-x-0 overflow-y-auto"
            : cn(
                "fixed inset-y-0 left-0 z-50 w-[min(100%,320px)]",
                mobileNavOpen ? "translate-x-0" : "-translate-x-full",
              ),
        )}
      >
        <div className="flex items-center justify-between px-2">
          <Link
            href="/app/dashboard"
            className={cn("flex min-w-0 items-center gap-3 rounded-2xl px-3 py-3", navCollapsed && "justify-center")}
            onClick={() => setMobileNavOpen(false)}
          >
            <div className="rounded-2xl bg-primary/12 p-2 text-primary">
              <Landmark className="h-5 w-5" />
            </div>
            {!navCollapsed ? (
              <div className="min-w-0">
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-primary">AI COO</p>
                <p className="text-xs text-muted-foreground">Executive operating system</p>
              </div>
            ) : null}
          </Link>
          <div className="flex shrink-0 items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className={cn(!isMdUp ? "inline-flex" : "hidden")}
              onClick={() => setMobileNavOpen(false)}
              aria-label="Close sidebar"
            >
              <X className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={cn(isMdUp ? "inline-flex" : "hidden")}
              onClick={() => setCollapsed(!collapsed)}
              aria-label="Toggle sidebar"
            >
              <ChevronsLeftRightEllipsis className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="mt-6 space-y-5">
          <PrimaryNav items={primaryNav} pathname={pathname} collapsed={navCollapsed} />
          <SecondaryNav items={secondaryNav} pathname={pathname} collapsed={navCollapsed} />
          {showAdvancedNav ? (
            <div className="space-y-1">
              {!navCollapsed ? <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Advanced</p> : null}
              <nav className="space-y-1">
                {advancedNav.map((item) => {
                  const Icon = item.icon;
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm transition",
                        navCollapsed && "justify-center px-0",
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
          ) : null}
        </div>
      </aside>

      <div className={cn("min-w-0", isMdUp && "h-dvh overflow-y-auto")}>
        <header className="sticky top-0 z-20 border-b border-border/70 bg-background/92 backdrop-blur-xl">
          <PageContainer className="flex flex-col gap-3 py-4">
            <TopBar>
              <div className={cn("min-w-[220px] flex-1", isMdUp && "max-w-sm")}>
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
              <div className={cn("min-w-[200px]", isMdUp && "max-w-xs")}>
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
                <ProfileMenu
                  email={user?.email}
                  role={selectedOrg?.role}
                  experienceTier={experienceTier}
                  onExperienceTierChange={setExperienceTier}
                  onLogout={async () => {
                    await logout();
                    clearSession();
                    router.replace("/auth/login");
                  }}
                />
              </div>
            </TopBar>
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
            <motion.div
              initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 8 }}
              animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
              transition={reduceMotion ? { duration: 0 } : { duration: 0.2, ease: "easeOut" }}
              className="min-w-0 pb-4"
            >
              {children}
            </motion.div>
          </PageContainer>
        </main>
      </div>
    </div>
  );
}
