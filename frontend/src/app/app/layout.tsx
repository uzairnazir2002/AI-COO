"use client";

import { AppShell } from "@/components/shell/app-shell";
import { Skeleton } from "@/components/ui/skeleton";
import { useSessionBootstrap } from "@/lib/auth/session";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { loading } = useSessionBootstrap(true);

  if (loading) {
    return (
      <div className="mx-auto mt-20 max-w-5xl space-y-4 px-4">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return <AppShell>{children}</AppShell>;
}
