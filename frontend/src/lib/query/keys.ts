export const qk = {
  me: ["me"] as const,
  orgs: ["orgs"] as const,
  summary: (orgId: string, from: string, to: string) => ["summary", orgId, from, to] as const,
  cashflow: (orgId: string, from: string, to: string, granularity: string) => ["cashflow", orgId, from, to, granularity] as const,
  runway: (orgId: string, lookback: number, conservative: boolean) => ["runway", orgId, lookback, conservative] as const,
  alerts: (orgId: string, status: string) => ["alerts", orgId, status] as const,
  transactions: (params: Record<string, string | number | undefined>) => ["transactions", params] as const,
  forecast: (orgId: string, months: number) => ["forecast", orgId, months] as const,
  reports: (orgId: string) => ["reports", orgId] as const,
  members: (orgId: string) => ["members", orgId] as const,
  settings: (orgId: string) => ["settings", orgId] as const,
};
