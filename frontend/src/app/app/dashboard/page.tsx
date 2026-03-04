import { Suspense } from "react";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";

import { Skeleton } from "@/components/ui/skeleton";
import { DashboardPageClient } from "@/features/dashboard/dashboard-page-client";
import { resolveServerOrgId } from "@/lib/api/server";
import { createServerQueryClient, prefetchDashboard } from "@/lib/query/prefetch";
import { startOfMonthISO, todayISO } from "@/lib/utils/format";

export default async function DashboardPage() {
  const queryClient = createServerQueryClient();
  const orgId = await resolveServerOrgId();
  const from = startOfMonthISO();
  const to = todayISO();

  if (orgId) {
    await prefetchDashboard(queryClient, orgId, from, to);
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <Suspense fallback={<Skeleton className="h-80 w-full" />}>
        <DashboardPageClient />
      </Suspense>
    </HydrationBoundary>
  );
}
