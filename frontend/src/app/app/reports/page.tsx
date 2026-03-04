import { Suspense } from "react";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";

import { Skeleton } from "@/components/ui/skeleton";
import { ReportsPageClient } from "@/features/reports/reports-page-client";
import { resolveServerOrgId } from "@/lib/api/server";
import { createServerQueryClient, prefetchReports } from "@/lib/query/prefetch";

export default async function ReportsPage() {
  const queryClient = createServerQueryClient();
  const orgId = await resolveServerOrgId();

  if (orgId) {
    await prefetchReports(queryClient, orgId);
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        <ReportsPageClient />
      </Suspense>
    </HydrationBoundary>
  );
}
