export const qk = {
  me: ["me"] as const,
  orgs: ["orgs"] as const,
  summary: (orgId: string, from: string, to: string, locationId: string = "") =>
    ["summary", orgId, from, to, locationId] as const,
  cashflow: (orgId: string, from: string, to: string, granularity: string, locationId: string = "") =>
    ["cashflow", orgId, from, to, granularity, locationId] as const,
  runway: (orgId: string, lookback: number, conservative: boolean, locationId: string = "") =>
    ["runway", orgId, lookback, conservative, locationId] as const,
  alerts: (orgId: string, status: string, assigneeUserId: string = "", locationId: string = "") =>
    ["alerts", orgId, status, assigneeUserId, locationId] as const,
  transactions: (params: Record<string, string | number | undefined>) => ["transactions", params] as const,
  budgets: (orgId: string, period: string, budgetType: string, includeHistory: boolean) =>
    ["budgets", orgId, period, budgetType, includeHistory] as const,
  budgetVariance: (orgId: string, period: string, budgetType: string, locationId: string = "") =>
    ["budgetVariance", orgId, period, budgetType, locationId] as const,
  locationBenchmark: (orgId: string, from: string, to: string) => ["locationBenchmark", orgId, from, to] as const,
  forecast: (orgId: string, months: number) => ["forecast", orgId, months] as const,
  reports: (orgId: string, locationId: string = "") => ["reports", orgId, locationId] as const,
  members: (orgId: string) => ["members", orgId] as const,
  settings: (orgId: string) => ["settings", orgId] as const,
  locations: (orgId: string, includeInactive: boolean) => ["locations", orgId, includeInactive] as const,
  billing: (orgId: string) => ["billing", orgId] as const,
  planUsage: (orgId: string) => ["planUsage", orgId] as const,
  bankConnections: (orgId: string) => ["bankConnections", orgId] as const,
  paymentConnections: (orgId: string, provider: string) => ["paymentConnections", orgId, provider] as const,
  paymentReconciliation: (orgId: string, provider: string, dateFrom: string, dateTo: string) =>
    ["paymentReconciliation", orgId, provider, dateFrom, dateTo] as const,
  inventoryItems: (orgId: string, locationId: string = "", includeInactive: boolean = false) =>
    ["inventoryItems", orgId, locationId, includeInactive] as const,
  inventoryForecast: (orgId: string, locationId: string = "", lookbackDays: number = 30, horizonDays: number = 30) =>
    ["inventoryForecast", orgId, locationId, lookbackDays, horizonDays] as const,
  imports: (orgId: string, page: number, pageSize: number) => ["imports", orgId, page, pageSize] as const,
  jobs: (orgId: string, params: Record<string, string | number | undefined>) => ["jobs", orgId, params] as const,
  outbox: (orgId: string, params: Record<string, string | number | undefined>) => ["outbox", orgId, params] as const,
  systemStatus: (orgId: string) => ["systemStatus", orgId] as const,
  notifications: (orgId: string, unreadOnly: boolean) => ["notifications", orgId, unreadOnly] as const,
  aiChatSessions: (orgId: string, mineOnly: boolean, limit: number) => ["aiChatSessions", orgId, mineOnly, limit] as const,
  aiChatSession: (orgId: string, sessionId: string) => ["aiChatSession", orgId, sessionId] as const,
};
