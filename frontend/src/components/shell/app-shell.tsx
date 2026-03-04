"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AlertTriangle, BarChart3, FileText, LineChart, LogOut, Settings2, Wallet } from "lucide-react";

import { ThemeToggle } from "@/components/common/theme-toggle";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { logout } from "@/lib/api/client";
import { useAppStore } from "@/store/appStore";
import { cn } from "@/lib/utils/cn";

const nav = [
  { href: "/app/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/app/transactions", label: "Transactions", icon: Wallet },
  { href: "/app/forecast", label: "Forecast", icon: LineChart },
  { href: "/app/alerts", label: "Alerts", icon: AlertTriangle },
  { href: "/app/reports", label: "Reports", icon: FileText },
  { href: "/app/settings", label: "Settings", icon: Settings2 },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const orgs = useAppStore((s) => s.orgs);
  const selectedOrgId = useAppStore((s) => s.selectedOrgId);
  const setSelectedOrgId = useAppStore((s) => s.setSelectedOrgId);
  const user = useAppStore((s) => s.user);
  const clearSession = useAppStore((s) => s.clearSession);

  useEffect(() => {
    if (!selectedOrgId || typeof document === "undefined") return;
    document.cookie = `ai_coo_selected_org=${selectedOrgId}; path=/; max-age=31536000; SameSite=Lax`;
  }, [selectedOrgId]);

  return (
    <div className="min-h-screen md:grid md:grid-cols-[260px_1fr]">
      <aside className="border-r border-border bg-card/60 p-4 backdrop-blur">
        <Link href="/app/dashboard" className="mb-8 block text-lg font-semibold">AI COO</Link>
        <nav className="space-y-1">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                  active ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                )}
              >
                <Icon className="h-4 w-4" /> {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex flex-wrap items-center gap-3 border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
          <div className="w-64">
            <Select
              value={selectedOrgId || (orgs[0]?.org_id ?? "__none__")}
              onValueChange={(value) => {
                if (value === "__none__") return;
                setSelectedOrgId(value);
                if (typeof document !== "undefined") {
                  document.cookie = `ai_coo_selected_org=${value}; path=/; max-age=31536000; SameSite=Lax`;
                }
                router.refresh();
              }}
            >
              <SelectTrigger aria-label="Organization switcher">
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
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <span className="hidden text-sm text-muted-foreground md:inline">{user?.email}</span>
            <Button
              size="sm"
              variant="outline"
              onClick={async () => {
                await logout();
                clearSession();
                router.replace("/auth/login");
              }}
            >
              <LogOut className="mr-2 h-4 w-4" /> Logout
            </Button>
          </div>
        </header>
        <main className="p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
