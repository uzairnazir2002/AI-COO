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
