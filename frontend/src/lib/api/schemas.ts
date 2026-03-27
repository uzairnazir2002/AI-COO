import { z } from "zod";

export const tokenSchema = z.object({
  access_token: z.string().nullable().optional(),
  refresh_token: z.string().nullable().optional(),
  token_type: z.string(),
  expires_in: z.number(),
});

export const meSchema = z.object({
  user: z.object({
    id: z.string().uuid(),
    email: z.string().email(),
    created_at: z.string(),
  }),
  orgs: z.array(
    z.object({
      org_id: z.string().uuid(),
      role: z.enum(["OWNER", "EDITOR", "VIEWER"]),
      name: z.string(),
    }),
  ),
});

export const summarySchema = z.object({
  cash_balance: z.string(),
  revenue_mtd: z.string(),
  expenses_mtd: z.string(),
  net_profit_mtd: z.string(),
  burn_rate_monthly: z.string(),
  alerts_count_open: z.number(),
});

export const aiSummarySchema = z.object({
  summary_json: z.object({
    headline: z.string(),
    highlights: z.array(z.string()),
    risks: z.array(z.string()),
    actions: z.array(z.string()),
    confidence: z.string(),
  }),
  fallback_used: z.boolean(),
});

export const aiChatSessionSchema = z.object({
  id: z.string().uuid(),
  org_id: z.string().uuid(),
  created_by_user_id: z.string().uuid(),
  title: z.string(),
  last_activity_at: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const aiChatMessageSchema = z.object({
  id: z.string().uuid(),
  session_id: z.string().uuid(),
  org_id: z.string().uuid(),
  created_by_user_id: z.string().uuid().nullable(),
  role: z.string(),
  content: z.string(),
  fallback_used: z.boolean(),
  grounding_violations: z.array(z.string()),
  created_at: z.string(),
});

export const aiChatSessionDetailSchema = z.object({
  session: aiChatSessionSchema,
  messages: z.array(aiChatMessageSchema),
});

export const aiChatResponseSchema = z.object({
  session_id: z.string().uuid(),
  message: aiChatMessageSchema,
});

export const registerOutSchema = z.object({
  user_id: z.string().uuid(),
  access_token: z.string().nullable().optional(),
  refresh_token: z.string().nullable().optional(),
  token_type: z.string().optional(),
  expires_in: z.number().nullable().optional(),
  account_confirmed: z.boolean().optional(),
});

export const resendConfirmationSchema = z.object({
  ok: z.boolean(),
  sent: z.boolean(),
  already_active: z.boolean(),
});

export const reportGenerateSchema = z.object({
  report_id: z.string().uuid().nullable().optional(),
  job_id: z.string(),
  status: z.string(),
});

export const jobSchema = z.object({
  id: z.string().uuid(),
  org_id: z.string().uuid().nullable(),
  task_id: z.string(),
  task_name: z.string(),
  dedupe_key: z.string(),
  status: z.string(),
  progress: z.number(),
  payload: z.record(z.string(), z.unknown()),
  result: z.record(z.string(), z.unknown()).nullable(),
  request_id: z.string().nullable(),
  correlation_id: z.string().nullable(),
  last_error: z.string().nullable(),
  traceback_summary: z.string().nullable(),
  retry_count: z.number(),
  last_retry_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const jobPageSchema = z.object({
  items: z.array(jobSchema),
  page: z.number(),
  page_size: z.number(),
  total: z.number(),
});

export const outboxEventSchema = z.object({
  id: z.string().uuid(),
  org_id: z.string().uuid().nullable(),
  event_type: z.string(),
  payload: z.record(z.string(), z.unknown()),
  status: z.string(),
  attempts: z.number(),
  max_attempts: z.number(),
  available_at: z.string(),
  sent_at: z.string().nullable(),
  last_error: z.string().nullable(),
  correlation_id: z.string().nullable(),
  dedupe_key: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const outboxPageSchema = z.object({
  items: z.array(outboxEventSchema),
  page: z.number(),
  page_size: z.number(),
  total: z.number(),
  counts_by_status: z.record(z.string(), z.number()),
});

export const beatScheduleSchema = z.object({
  name: z.string(),
  task: z.string(),
  schedule: z.string(),
  paused: z.boolean(),
});

export const systemStatusSchema = z.object({
  scheduler: z.array(beatScheduleSchema),
  system_jobs: z.array(jobSchema),
  system_job_total: z.number(),
  org_outbox_counts: z.record(z.string(), z.number()),
});

export const endpointSloSchema = z.object({
  endpoint: z.string(),
  requests: z.number(),
  p95_ms: z.number(),
  error_rate_pct: z.number(),
  breach: z.boolean(),
});

export const runtimeSloSchema = z.object({
  org_id: z.string().uuid(),
  window_seconds: z.number(),
  p95_threshold_ms: z.number(),
  error_rate_threshold_pct: z.number(),
  total_requests: z.number(),
  endpoints: z.array(endpointSloSchema),
});

export const runtimeMetricsSchema = z.object({
  org_id: z.string().uuid(),
  queue_depth_active: z.number(),
  queue_lag_seconds: z.number(),
  queue_lag_breach: z.boolean(),
  outbox_pending: z.number(),
  dead_letter_open: z.number(),
  worker_health: z.string(),
  db_active_connections: z.number(),
  auth_lockout_failures_total: z.number(),
  auth_lockouts_total: z.number(),
  auth_lockout_escalations_total: z.number(),
});

export const deadLetterEventSchema = z.object({
  id: z.string().uuid(),
  org_id: z.string().uuid().nullable(),
  source_type: z.string(),
  source_id: z.string().uuid().nullable(),
  source_task_id: z.string().nullable(),
  source_name: z.string(),
  status: z.string(),
  attempts: z.number(),
  last_error: z.string().nullable(),
  payload: z.record(z.string(), z.unknown()),
  metadata_json: z.record(z.string(), z.unknown()),
  first_failed_at: z.string(),
  last_failed_at: z.string(),
  replayed_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string().nullable(),
});

export const deadLetterPageSchema = z.object({
  items: z.array(deadLetterEventSchema),
  page: z.number(),
  page_size: z.number(),
  total: z.number(),
  counts_by_status: z.record(z.string(), z.number()),
});

export const notificationItemSchema = z.object({
  id: z.string().uuid(),
  org_id: z.string().uuid().nullable(),
  user_id: z.string().uuid().nullable(),
  category: z.string(),
  title: z.string(),
  message: z.string().nullable(),
  link: z.string().nullable(),
  is_read: z.boolean(),
  metadata_json: z.record(z.string(), z.unknown()),
  created_at: z.string(),
});

export const notificationPageSchema = z.object({
  items: z.array(notificationItemSchema),
  page: z.number(),
  page_size: z.number(),
  total: z.number(),
  unread_count: z.number(),
});

export const billingUrlSchema = z.object({
  url: z.string().url(),
});

export const deletionRequestItemSchema = z.object({
  id: z.string().uuid(),
  scope: z.string(),
  status: z.string(),
  requested_by_user_id: z.string().uuid().nullable(),
  target_user_id: z.string().uuid().nullable(),
  target_org_id: z.string().uuid().nullable(),
  reason: z.string().nullable(),
  delete_after: z.string(),
  processed_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const deletionRequestListSchema = z.object({
  items: z.array(deletionRequestItemSchema),
});

export const paymentReconciliationSchema = z.object({
  org_id: z.string().uuid(),
  provider: z.string(),
  date_from: z.string(),
  date_to: z.string(),
  processor: z.object({
    inflow: z.string(),
    outflow: z.string(),
    net: z.string(),
    entry_count: z.number(),
  }),
  transactions: z.object({
    revenue: z.string(),
    expense: z.string(),
    net: z.string(),
    entry_count: z.number(),
  }),
  delta: z.object({
    net: z.string(),
    absolute: z.string(),
  }),
});

export const budgetSchema = z.object({
  id: z.string().uuid(),
  org_id: z.string().uuid(),
  created_by_user_id: z.string().uuid(),
  category: z.string(),
  period_month: z.string(),
  budget_type: z.string(),
  planned_amount: z.string(),
  notes: z.string().nullable(),
  version: z.number(),
  is_current: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const budgetVarianceLineSchema = z.object({
  category: z.string(),
  budget_type: z.string(),
  planned_amount: z.string(),
  actual_amount: z.string(),
  variance_amount: z.string(),
  variance_pct: z.string().nullable(),
});

export const budgetVarianceSchema = z.object({
  org_id: z.string().uuid(),
  period_month: z.string(),
  budget_type: z.string(),
  totals: z.object({
    planned_amount: z.string(),
    actual_amount: z.string(),
    variance_amount: z.string(),
  }),
  lines: z.array(budgetVarianceLineSchema),
});

export const locationBenchmarkItemSchema = z.object({
  location_id: z.string().uuid().nullable(),
  location_name: z.string(),
  transaction_count: z.number(),
  revenue: z.string(),
  expense: z.string(),
  net: z.string(),
  margin_pct: z.string().nullable(),
  revenue_share_pct: z.string().nullable(),
  expense_share_pct: z.string().nullable(),
});

export const locationBenchmarkSchema = z.object({
  org_id: z.string().uuid(),
  from_date: z.string(),
  to_date: z.string(),
  totals: z.object({
    revenue: z.string(),
    expense: z.string(),
    net: z.string(),
  }),
  locations: z.array(locationBenchmarkItemSchema),
});

export const inventoryItemSchema = z.object({
  id: z.string().uuid(),
  org_id: z.string().uuid(),
  location_id: z.string().uuid().nullable(),
  created_by_user_id: z.string().uuid(),
  sku: z.string(),
  name: z.string(),
  unit_cost: z.string(),
  reorder_point: z.string(),
  is_active: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const inventoryStockEventSchema = z.object({
  id: z.string().uuid(),
  org_id: z.string().uuid(),
  item_id: z.string().uuid(),
  location_id: z.string().uuid().nullable(),
  event_type: z.string(),
  quantity: z.string(),
  delta_qty: z.string(),
  unit_cost: z.string().nullable(),
  occurred_at: z.string(),
  reference: z.string().nullable(),
  notes: z.string().nullable(),
  created_by_user_id: z.string().uuid(),
  created_at: z.string(),
});

export const inventoryPurchaseOrderSchema = z.object({
  id: z.string().uuid(),
  org_id: z.string().uuid(),
  item_id: z.string().uuid(),
  location_id: z.string().uuid().nullable(),
  quantity: z.string(),
  received_qty: z.string(),
  unit_cost: z.string().nullable(),
  expected_date: z.string(),
  status: z.string(),
  external_ref: z.string().nullable(),
  created_by_user_id: z.string().uuid(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const inventoryForecastItemSchema = z.object({
  item_id: z.string().uuid(),
  sku: z.string(),
  name: z.string(),
  location_id: z.string().uuid().nullable(),
  on_hand_qty: z.string(),
  inbound_open_qty: z.string(),
  units_per_day: z.string(),
  days_of_cover: z.string().nullable(),
  projected_stockout_date: z.string().nullable(),
  risk_level: z.string(),
  reorder_point: z.string(),
  cogs_exposure_30d: z.string(),
});

export const inventoryForecastSchema = z.object({
  generated_at: z.string(),
  lookback_days: z.number(),
  horizon_days: z.number(),
  items: z.array(inventoryForecastItemSchema),
  high_risk_items: z.number(),
});

export type TokenResponse = z.infer<typeof tokenSchema>;
export type MeResponse = z.infer<typeof meSchema>;
export type SummaryResponse = z.infer<typeof summarySchema>;
export type AiSummaryResponse = z.infer<typeof aiSummarySchema>;
export type AiChatSessionResponse = z.infer<typeof aiChatSessionSchema>;
export type AiChatMessageResponse = z.infer<typeof aiChatMessageSchema>;
export type AiChatSessionDetailResponse = z.infer<typeof aiChatSessionDetailSchema>;
export type AiChatResponse = z.infer<typeof aiChatResponseSchema>;
export type RegisterOutResponse = z.infer<typeof registerOutSchema>;
export type ResendConfirmationResponse = z.infer<typeof resendConfirmationSchema>;
export type ReportGenerateResponse = z.infer<typeof reportGenerateSchema>;
export type JobPageResponse = z.infer<typeof jobPageSchema>;
export type OutboxPageResponse = z.infer<typeof outboxPageSchema>;
export type SystemStatusResponse = z.infer<typeof systemStatusSchema>;
export type RuntimeSloResponse = z.infer<typeof runtimeSloSchema>;
export type RuntimeMetricsResponse = z.infer<typeof runtimeMetricsSchema>;
export type DeadLetterPageResponse = z.infer<typeof deadLetterPageSchema>;
export type NotificationPageResponse = z.infer<typeof notificationPageSchema>;
export type BillingUrlResponse = z.infer<typeof billingUrlSchema>;
export type DeletionRequestListResponse = z.infer<typeof deletionRequestListSchema>;
export type PaymentReconciliationResponse = z.infer<typeof paymentReconciliationSchema>;
export type BudgetResponse = z.infer<typeof budgetSchema>;
export type BudgetVarianceResponse = z.infer<typeof budgetVarianceSchema>;
export type LocationBenchmarkResponse = z.infer<typeof locationBenchmarkSchema>;
export type InventoryItemResponse = z.infer<typeof inventoryItemSchema>;
export type InventoryStockEventResponse = z.infer<typeof inventoryStockEventSchema>;
export type InventoryPurchaseOrderResponse = z.infer<typeof inventoryPurchaseOrderSchema>;
export type InventoryForecastResponse = z.infer<typeof inventoryForecastSchema>;
