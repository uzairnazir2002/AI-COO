"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Activity as ActivityIcon,
  AlertTriangle,
  BarChart3,
  Boxes,
  ChevronsLeftRightEllipsis,
  FileText,
  Landmark,
  LineChart,
  LogOut,
  MessageSquare,
  PiggyBank,
  Settings2,
  Wallet,
} from "lucide-react";

import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { CommandPalette } from "@/components/shell/command-palette";
import { DateRangeControl } from "@/components/shell/date-range-control";
import { NotificationCenter } from "@/components/shell/notification-center";
import { ThemeToggle } from "@/components/common/theme-toggle";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useLocations } from "@/features/locations/hooks";
import { useOrgEventFeed } from "@/features/notifications/hooks";
import { logout } from "@/lib/api/client";
import { useAppStore } from "@/store/appStore";
import { cn } from "@/lib/utils/cn";

const nav = [
  { href: "/app/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/app/activity", label: "Activity", icon: ActivityIcon },
  { href: "/app/transactions", label: "Transactions", icon: Wallet },
  { href: "/app/inventory", label: "Inventory", icon: Boxes },
  { href: "/app/budgets", label: "Budgets", icon: PiggyBank },
  { href: "/app/forecast", label: "Forecast", icon: LineChart },
  { href: "/app/assistant", label: "AI Chat", icon: MessageSquare },
  { href: "/app/alerts", label: "Alerts", icon: AlertTriangle },
  { href: "/app/reports", label: "Reports", icon: FileText },
  { href: "/app/settings", label: "Settings", icon: Settings2 },
];

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

  useEffect(() => {
    if (!selectedOrgId || typeof document === "undefined") return;
    document.cookie = `ai_coo_selected_org=${selectedOrgId}; path=/; max-age=31536000; SameSite=Lax`;
  }, [selectedOrgId]);

  return (
    <div className="min-h-screen md:grid" style={{ gridTemplateColumns: collapsed ? "92px 1fr" : "290px 1fr" }}>
      <aside className="border-r border-border/70 bg-card/65 px-3 py-4 backdrop-blur-xl">
        <div className="flex items-center justify-between px-2">
          <Link href="/app/dashboard" className={cn("flex items-center gap-3 rounded-2xl px-3 py-3", collapsed && "justify-center")}>
            <div className="rounded-2xl bg-primary/12 p-2 text-primary">
              <Landmark className="h-5 w-5" />
            </div>
            {!collapsed ? (
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-primary">AI COO</p>
                <p className="text-xs text-muted-foreground">Executive cockpit</p>
              </div>
            ) : null}
          </Link>
          <Button variant="ghost" size="icon" className="hidden md:inline-flex" onClick={() => setCollapsed(!collapsed)} aria-label="Toggle sidebar">
            <ChevronsLeftRightEllipsis className="h-4 w-4" />
          </Button>
        </div>
        <nav className="mt-8 space-y-1">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-2xl px-3 py-3 text-sm transition",
                  collapsed && "justify-center px-0",
                  active ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20" : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
                aria-current={active ? "page" : undefined}
              >
                <Icon className="h-4 w-4" />
                {!collapsed ? <span>{item.label}</span> : null}
              </Link>
            );
          })}
        </nav>
        {!collapsed ? (
          <div className="mt-8 rounded-[24px] border border-border/70 bg-background/65 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Workspace</p>
            <p className="mt-2 text-sm font-medium">Everything stays org-scoped.</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">Routes, RBAC, auth mode, and org context remain backed by the current API.</p>
          </div>
        ) : null}
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 border-b border-border/70 bg-background/90 backdrop-blur-xl">
          <div className="page-container flex flex-col gap-4 py-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="min-w-[220px] flex-1 md:max-w-sm">
                <Select
                  value={selectedOrgId || (orgs[0]?.org_id ?? "__none__")}
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
                  <SelectTrigger aria-label="Organization switcher" className="h-11 rounded-2xl bg-card/75">
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
                  <SelectTrigger aria-label="Location scope switcher" className="h-11 rounded-2xl bg-card/75">
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
                <ThemeToggle />
                <div className="hidden rounded-2xl border border-border bg-card/80 px-3 py-2 text-right md:block">
                  <p className="max-w-[180px] truncate text-sm font-medium">{user?.email}</p>
                  <p className="text-xs text-muted-foreground">Secure session</p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={async () => {
                    await logout();
                    clearSession();
                    router.replace("/auth/login");
                  }}
                  className="rounded-2xl"
                >
                  <LogOut className="mr-2 h-4 w-4" /> Logout
                </Button>
              </div>
            </div>
            <Breadcrumbs />
          </div>
        </header>
        <main className="page-container">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="min-w-0">
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  );
}
