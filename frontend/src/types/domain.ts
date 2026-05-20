export type Role = "OWNER" | "EDITOR" | "MANAGER" | "VIEWER";

export type Org = { org_id: string; name: string; role?: Role };
export type Member = { user_id: string; email: string; role: Role };

export type Transaction = {
  id: string;
  org_id: string;
  location_id?: string | null;
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

export type AiChatSession = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  title: string;
  last_activity_at: string;
  created_at: string;
  updated_at: string;
};

export type AiChatMessage = {
  id: string;
  session_id: string;
  org_id: string;
  created_by_user_id: string | null;
  role: string;
  content: string;
  fallback_used: boolean;
  grounding_violations: string[];
  created_at: string;
};

export type AiChatSessionDetail = {
  session: AiChatSession;
  messages: AiChatMessage[];
};

export type Budget = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  category: string;
  period_month: string;
  budget_type: "EXPENSE" | "REVENUE" | string;
  planned_amount: string;
  notes: string | null;
  version: number;
  is_current: boolean;
  created_at: string;
  updated_at: string;
};

export type BudgetVarianceLine = {
  category: string;
  budget_type: string;
  planned_amount: string;
  actual_amount: string;
  variance_amount: string;
  variance_pct: string | null;
};

export type BudgetVariance = {
  org_id: string;
  period_month: string;
  budget_type: string;
  totals: {
    planned_amount: string;
    actual_amount: string;
    variance_amount: string;
  };
  lines: BudgetVarianceLine[];
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
  location_id?: string | null;
  kind: "ANOMALY" | "PROFIT_LEAK" | "RUNWAY";
  severity: "LOW" | "MEDIUM" | "HIGH";
  title: string;
  description: string;
  meta: Record<string, unknown>;
  status: "OPEN" | "DISMISSED";
  assigned_to_user_id?: string | null;
  assigned_by_user_id?: string | null;
  assigned_at?: string | null;
  acknowledged_at?: string | null;
  created_at: string;
};

export type AlertHistoryItem = {
  id: string;
  action: "alert.assign" | "alert.acknowledge" | "alert.dismiss" | string;
  actor_user_id: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type Report = {
  id: string;
  location_id?: string | null;
  week_start: string;
  week_end: string;
  created_at: string;
};

export type InventoryItem = {
  id: string;
  org_id: string;
  location_id: string | null;
  created_by_user_id: string;
  sku: string;
  name: string;
  unit_cost: string;
  reorder_point: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type InventoryStockEvent = {
  id: string;
  org_id: string;
  item_id: string;
  location_id: string | null;
  event_type: "INBOUND" | "OUTBOUND" | "ADJUSTMENT" | string;
  quantity: string;
  delta_qty: string;
  unit_cost: string | null;
  occurred_at: string;
  reference: string | null;
  notes: string | null;
  created_by_user_id: string;
  created_at: string;
};

export type InventoryPurchaseOrder = {
  id: string;
  org_id: string;
  item_id: string;
  location_id: string | null;
  quantity: string;
  received_qty: string;
  unit_cost: string | null;
  expected_date: string;
  status: string;
  external_ref: string | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
};

export type InventoryForecastItem = {
  item_id: string;
  sku: string;
  name: string;
  location_id: string | null;
  on_hand_qty: string;
  inbound_open_qty: string;
  units_per_day: string;
  days_of_cover: string | null;
  projected_stockout_date: string | null;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | string;
  reorder_point: string;
  cogs_exposure_30d: string;
};

export type InventoryForecast = {
  generated_at: string;
  lookback_days: number;
  horizon_days: number;
  items: InventoryForecastItem[];
  high_risk_items: number;
};

export type Location = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  name: string;
  code: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkforceDepartment = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  name: string;
  code: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkforceTitle = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  name: string;
  level: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkforceEmployee = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  employee_code: string | null;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  department_id: string | null;
  title_id: string | null;
  manager_employee_id: string | null;
  location_id: string | null;
  employment_type: string;
  employment_status: string;
  start_date: string | null;
  end_date: string | null;
  contract_start?: string | null;
  contract_end?: string | null;
  probation_end?: string | null;
  salary_type: string;
  base_salary: string | null;
  hourly_rate: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkforcePolicy = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  code: string;
  title: string;
  body: string;
  version: number;
  requires_ack: boolean;
  is_active: boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkforcePolicyAck = {
  id: string;
  org_id: string;
  policy_id: string;
  employee_id: string;
  acknowledged_at: string;
  acknowledged_by_user_id: string;
};

export type WorkforceDocument = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  employee_id: string | null;
  policy_id: string | null;
  name: string;
  content_type: string;
  size_bytes: number;
  object_key: string;
  url: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkforceChecklistItem = {
  id: string;
  org_id: string;
  employee_id: string;
  kind: string;
  title: string;
  details: string | null;
  due_date: string | null;
  is_done: boolean;
  completed_at: string | null;
  completed_by_user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkforceShift = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  name: string;
  start_time: string;
  end_time: string;
  grace_minutes: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkforceShiftAssignment = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  employee_id: string;
  shift_id: string;
  effective_from: string;
  effective_to: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkforceAttendance = {
  id: string;
  org_id: string;
  employee_id: string;
  created_by_user_id: string;
  work_date: string;
  status: string;
  source: string;
  shift_id: string | null;
  shift_assignment_id: string | null;
  clock_in_at: string | null;
  clock_out_at: string | null;
  is_late: boolean;
  minutes_late: number;
  missing_checkout: boolean;
  worked_minutes: number;
  overtime_minutes: number;
  payable_hours: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkforceAttendanceDaily = {
  org_id: string;
  date: string;
  items: WorkforceAttendance[];
};

export type WorkforceAttendanceCalendarDay = {
  date: string;
  totals: Record<string, number>;
  late_count: number;
  missing_checkout_count: number;
};

export type WorkforceAttendanceCalendar = {
  org_id: string;
  month: string;
  days: WorkforceAttendanceCalendarDay[];
};

export type WorkforceAttendanceCorrection = {
  id: string;
  org_id: string;
  employee_id: string;
  attendance_record_id: string;
  requested_by_user_id: string;
  reviewed_by_user_id: string | null;
  status: string;
  reason: string;
  proposed_clock_in_at: string | null;
  proposed_clock_out_at: string | null;
  proposed_status: string | null;
  reviewer_note: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkforceAnnouncementReceipt = {
  read_at: string | null;
  acknowledged_at: string | null;
};

export type WorkforceAnnouncementAttachment = {
  name: string;
  url: string;
};

export type WorkforceAnnouncement = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  template_id?: string | null;
  title: string;
  body: string;
  priority: string;
  status: string;
  published_at: string | null;
  scheduled_publish_at: string | null;
  expires_at: string | null;
  pinned: boolean;
  acknowledgement_required: boolean;
  audience_kind: string;
  audience_ids?: string[] | null;
  attachments_json?: WorkforceAnnouncementAttachment[] | null;
  send_email_on_publish: boolean;
  automation_dedupe_key?: string | null;
  created_at: string;
  updated_at: string;
  my_receipt?: WorkforceAnnouncementReceipt | null;
};

export type WorkforceAnnouncementTemplate = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  name: string;
  code: string | null;
  description: string | null;
  body_template: string;
  automation_key: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkforceAnnouncementDelivery = {
  id: string;
  org_id: string;
  announcement_id: string;
  channel: string;
  user_id: string | null;
  recipient_email: string;
  status: string;
  error: string | null;
  outbox_event_id: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
  outbox_status?: string | null;
  outbox_attempts?: number | null;
  outbox_last_error?: string | null;
};

export type WorkforceAnnouncementDeliveryList = {
  items: WorkforceAnnouncementDelivery[];
  total: number;
  page: number;
  page_size: number;
};

export type WorkforceLeaveType = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  name: string;
  code: string | null;
  is_paid: boolean;
  requires_approval: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkforceLeaveBalance = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  employee_id: string;
  leave_type_id: string;
  year: number;
  allocated_days: string;
  used_days: string;
  pending_days: string;
  created_at: string;
  updated_at: string;
};

export type WorkforceLeaveRequest = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  employee_id: string;
  leave_type_id: string;
  start_date: string;
  end_date: string;
  days: string;
  status: string;
  reason: string | null;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  reviewer_note: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkforcePayrollPeriod = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  start_date: string;
  end_date: string;
  status: string;
  approved_by_user_id: string | null;
  approved_at: string | null;
  paid_by_user_id: string | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkforcePayrollEntry = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  payroll_period_id: string;
  employee_id: string;
  salary_type: string;
  base_salary: string | null;
  hourly_rate: string | null;
  overtime_multiplier: string | null;
  worked_minutes: number;
  overtime_minutes: number;
  payable_hours: string | null;
  unpaid_leave_deduction: string | null;
  gross_pay: string | null;
  adjustments_total: string | null;
  net_pay: string | null;
  status: string;
  is_locked: boolean;
  created_at: string;
  updated_at: string;
};

export type WorkforcePayrollAdjustment = {
  id: string;
  org_id: string;
  created_by_user_id: string;
  payroll_period_id: string;
  payroll_entry_id: string;
  employee_id: string;
  kind: string;
  amount: string | null;
  label: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkforcePayslipPreview = {
  entry: WorkforcePayrollEntry;
  adjustments: WorkforcePayrollAdjustment[];
  period: WorkforcePayrollPeriod;
};

export type OrgSettings = {
  org_id: string;
  starting_cash: string;
  runway_alert_threshold_days: number;
  vendor_concentration_threshold_pct: string;
  budget_variance_alert_threshold_pct: string;
  misc_growth_multiplier: string;
  anomaly_spike_multiplier: string;
  owner_mfa_required: boolean;
  owner_session_max_minutes: number;
  sensitive_action_reauth_minutes: number;
  workforce_org_context_canonical?: boolean;
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

export type EndpointSLO = {
  endpoint: string;
  requests: number;
  p95_ms: number;
  error_rate_pct: number;
  breach: boolean;
};

export type RuntimeSLO = {
  org_id: string;
  window_seconds: number;
  p95_threshold_ms: number;
  error_rate_threshold_pct: number;
  total_requests: number;
  endpoints: EndpointSLO[];
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

export type MfaStatus = {
  enabled: boolean;
  configured: boolean;
  enabled_at: string | null;
  recovery_codes_remaining: number;
};

export type AuthSession = {
  id: string;
  created_at: string;
  expires_at: string;
  last_used_at: string | null;
  user_agent: string | null;
  ip_address: string | null;
  is_revoked: boolean;
  is_current: boolean;
};

export type BillingCheckoutResult = {
  url: string;
};

export type BillingPortalResult = {
  url: string;
};

export type DeletionRequestResult = {
  ok: boolean;
  request_id: string;
  delete_after: string;
};

export type PiiRotationResult = {
  ok: boolean;
  updated_users: number;
  updated_org_settings: number;
  rotated_at: string;
};

export type DeletionRequestItem = {
  id: string;
  scope: "USER" | "ORG" | string;
  status: "PENDING" | "PROCESSED" | "CANCELLED" | string;
  requested_by_user_id: string | null;
  target_user_id: string | null;
  target_org_id: string | null;
  reason: string | null;
  delete_after: string;
  processed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type DeletionRequestList = {
  items: DeletionRequestItem[];
};

export type BankAccount = {
  id: string;
  external_account_id: string;
  name: string;
  mask: string | null;
  account_type: string | null;
  account_subtype: string | null;
  currency_code: string | null;
  is_active: boolean;
};

export type BankConnection = {
  id: string;
  org_id: string;
  provider: string;
  status: string;
  institution_id: string | null;
  institution_name: string | null;
  connected_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  revoked_at: string | null;
  accounts: BankAccount[];
};

export type PlaidLinkTokenResult = {
  link_token: string;
  expiration: string | null;
};

export type PaymentConnection = {
  id: string;
  org_id: string;
  provider: string;
  status: string;
  provider_account_id: string | null;
  connected_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  metadata_json: Record<string, unknown>;
};

export type StripeConnectResult = {
  connection: PaymentConnection;
};

export type PaymentReconciliation = {
  org_id: string;
  provider: string;
  date_from: string;
  date_to: string;
  processor: {
    inflow: string;
    outflow: string;
    net: string;
    entry_count: number;
  };
  transactions: {
    revenue: string;
    expense: string;
    net: string;
    entry_count: number;
  };
  delta: {
    net: string;
    absolute: string;
  };
};
