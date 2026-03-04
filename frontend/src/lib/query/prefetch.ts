import { QueryClient } from "@tanstack/react-query";

import { qk } from "@/lib/query/keys";
import { serverApiGet, serverApiPost } from "@/lib/api/server";

export function createServerQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
      },
    },
  });
}

export async function prefetchDashboard(queryClient: QueryClient, orgId: string, from: string, to: string) {
  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: qk.summary(orgId, from, to),
      queryFn: async () => serverApiGet(`/api/v1/analytics/summary?org_id=${orgId}&from=${from}&to=${to}`),
    }),
    queryClient.prefetchQuery({
      queryKey: qk.cashflow(orgId, from, to, "week"),
      queryFn: async () => serverApiGet(`/api/v1/analytics/cashflow?org_id=${orgId}&from=${from}&to=${to}&granularity=week`),
    }),
    queryClient.prefetchQuery({
      queryKey: qk.runway(orgId, 6, true),
      queryFn: async () => serverApiGet(`/api/v1/runway?org_id=${orgId}&lookback_months=6&conservative=true`),
    }),
    queryClient.prefetchQuery({
      queryKey: qk.alerts(orgId, "open"),
      queryFn: async () => serverApiGet(`/api/v1/alerts?org_id=${orgId}&status=open`),
    }),
    queryClient.prefetchQuery({
      queryKey: ["ai", orgId, from, to],
      queryFn: async () => serverApiPost(`/api/v1/ai/summary`, { org_id: orgId, from, to }),
    }),
  ]);
}

export async function prefetchReports(queryClient: QueryClient, orgId: string) {
  await queryClient.prefetchQuery({
    queryKey: qk.reports(orgId),
    queryFn: async () => serverApiGet(`/api/v1/reports?org_id=${orgId}`),
  });
}
