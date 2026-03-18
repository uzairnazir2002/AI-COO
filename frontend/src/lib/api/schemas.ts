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

export type TokenResponse = z.infer<typeof tokenSchema>;
export type MeResponse = z.infer<typeof meSchema>;
export type SummaryResponse = z.infer<typeof summarySchema>;
export type AiSummaryResponse = z.infer<typeof aiSummarySchema>;
export type RegisterOutResponse = z.infer<typeof registerOutSchema>;
export type ResendConfirmationResponse = z.infer<typeof resendConfirmationSchema>;
export type ReportGenerateResponse = z.infer<typeof reportGenerateSchema>;
export type JobPageResponse = z.infer<typeof jobPageSchema>;
export type OutboxPageResponse = z.infer<typeof outboxPageSchema>;
export type SystemStatusResponse = z.infer<typeof systemStatusSchema>;
export type NotificationPageResponse = z.infer<typeof notificationPageSchema>;
export type BillingUrlResponse = z.infer<typeof billingUrlSchema>;
