export type Role = "OWNER" | "EDITOR" | "VIEWER";

export type Org = { org_id: string; name: string; role?: Role };
export type Member = { user_id: string; email: string; role: Role };

export type Transaction = {
  id: string;
  org_id: string;
  date: string;
  amount: string;
  type: "REVENUE" | "EXPENSE";
  category: string;
  vendor?: string | null;
  notes?: string | null;
};

export type PaginatedTransactions = {
  items: Transaction[];
  page: number;
  page_size: number;
  total: number;
};

export type Summary = {
  cash_balance: string;
  revenue_mtd: string;
  expenses_mtd: string;
  net_profit_mtd: string;
  burn_rate_monthly: string;
  alerts_count_open: number;
};

export type Cashflow = {
  points: Array<{ date: string; revenue: string; expense: string; net: string }>;
};

export type Runway = {
  runway_days: number;
  monthly_burn: string;
  cash_balance: string;
  alert: boolean;
};

export type ForecastPoint = {
  month: string;
  revenue_pred: string;
  expense_pred: string;
  confidence_low: string;
  confidence_high: string;
};

export type Forecast = {
  scenarios: {
    base: ForecastPoint[];
    high: ForecastPoint[];
    low: ForecastPoint[];
  };
  generated_at: string;
};

export type Alert = {
  id: string;
  org_id: string;
  kind: "ANOMALY" | "PROFIT_LEAK" | "RUNWAY";
  severity: "LOW" | "MEDIUM" | "HIGH";
  title: string;
  description: string;
  meta: Record<string, unknown>;
  status: "OPEN" | "DISMISSED";
  created_at: string;
};

export type Report = {
  id: string;
  week_start: string;
  week_end: string;
  created_at: string;
};

export type OrgSettings = {
  org_id: string;
  starting_cash: string;
  runway_alert_threshold_days: number;
  vendor_concentration_threshold_pct: string;
  misc_growth_multiplier: string;
  anomaly_spike_multiplier: string;
};

export type OrgBilling = {
  org_id: string;
  billing_email: string | null;
  invoice_enabled: boolean;
  plan_label: string;
  billing_notes: string | null;
  provider: string;
  customer_id: string | null;
  subscription_id: string | null;
  subscription_status: string | null;
  current_period_end: string | null;
  active_price_id: string | null;
  publishable_key?: string | null;
};

export type PlanUsage = {
  plan_code: string;
  period_start: string;
  metrics: Record<string, { used: number; limit: number }>;
};

export type Job = {
  id: string;
  org_id: string | null;
  task_id: string;
  task_name: string;
  dedupe_key: string;
  status: "PENDING" | "RUNNING" | "RETRYING" | "SUCCEEDED" | "FAILED" | string;
  progress: number;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  request_id: string | null;
  correlation_id: string | null;
  last_error: string | null;
  traceback_summary: string | null;
  retry_count: number;
  last_retry_at: string | null;
  created_at: string;
  updated_at: string;
};

export type JobPage = {
  items: Job[];
  page: number;
  page_size: number;
  total: number;
};

export type AnalyticsRecomputeResult = {
  ok: boolean;
  job_id: string;
  status: string;
  result?: Record<string, unknown> | null;
};

export type AdminRecomputeResult = {
  ok: boolean;
  jobs: {
    monthly_aggregates: string;
    forecasts: string;
    alerts: string;
    report_object_verify: string;
  };
};

export type ResendConfirmationResult = {
  ok: boolean;
  sent: boolean;
  already_active: boolean;
};

export type ReportGenerationResult = {
  report_id?: string | null;
  job_id: string;
  status: string;
};

export type OutboxEvent = {
  id: string;
  org_id: string | null;
  event_type: string;
  payload: Record<string, unknown>;
  status: string;
  attempts: number;
  max_attempts: number;
  available_at: string;
  sent_at: string | null;
  last_error: string | null;
  correlation_id: string | null;
  dedupe_key: string | null;
  created_at: string;
  updated_at: string;
};

export type OutboxPage = {
  items: OutboxEvent[];
  page: number;
  page_size: number;
  total: number;
  counts_by_status: Record<string, number>;
};

export type BeatScheduleItem = {
  name: string;
  task: string;
  schedule: string;
  paused: boolean;
};

export type SystemStatus = {
  scheduler: BeatScheduleItem[];
  system_jobs: Job[];
  system_job_total: number;
  org_outbox_counts: Record<string, number>;
};

export type StreamUpdate = {
  org_id: string;
  summary: Record<string, string>;
  open_alerts: number;
  ts: string;
};

export type ImportHistoryItem = {
  id: string;
  file_name: string;
  status: string;
  total_rows: number;
  inserted_count: number;
  duplicate_count: number;
  error_count: number;
  mapping_profile_id?: string | null;
  created_at: string;
  created_by: string;
};

export type ImportHistoryPage = {
  items: ImportHistoryItem[];
  page: number;
  page_size: number;
  total: number;
};

export type ImportMappingProfile = {
  id: string;
  org_id: string;
  user_id: string | null;
  name: string;
  column_map: Record<string, string>;
  created_at: string;
  updated_at: string;
};

export type NotificationItem = {
  id: string;
  org_id: string | null;
  user_id: string | null;
  category: string;
  title: string;
  message: string | null;
  link: string | null;
  is_read: boolean;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type NotificationPage = {
  items: NotificationItem[];
  page: number;
  page_size: number;
  total: number;
  unread_count: number;
};

export type BillingCheckoutResult = {
  url: string;
};

export type BillingPortalResult = {
  url: string;
};
