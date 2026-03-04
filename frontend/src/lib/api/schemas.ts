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

export type TokenResponse = z.infer<typeof tokenSchema>;
export type MeResponse = z.infer<typeof meSchema>;
export type SummaryResponse = z.infer<typeof summarySchema>;
export type AiSummaryResponse = z.infer<typeof aiSummarySchema>;
