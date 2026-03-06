"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";

const labels: Record<string, string> = {
  app: "Workspace",
  dashboard: "Dashboard",
  transactions: "Transactions",
  forecast: "Forecast",
  alerts: "Alerts",
  reports: "Reports",
  settings: "Settings",
  orgs: "Organizations",
};

export function Breadcrumbs() {
  const pathname = usePathname();
  const parts = pathname.split("/").filter(Boolean);
  const usable = parts[0] === "app" ? parts : [];

  return (
    <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
      {usable.map((part, index) => {
        const href = `/${usable.slice(0, index + 1).join("/")}`;
        const isLast = index === usable.length - 1;
        return (
          <span key={href} className="flex items-center gap-1">
            {index > 0 ? <ChevronRight className="h-3.5 w-3.5" /> : null}
            {isLast ? (
              <span className="font-medium text-foreground">{labels[part] ?? part}</span>
            ) : (
              <Link href={href} className="transition hover:text-foreground">
                {labels[part] ?? part}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
