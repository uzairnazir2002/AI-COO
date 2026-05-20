import uuid
from decimal import Decimal

from pydantic import BaseModel, EmailStr, field_validator


class OrganizationCreateIn(BaseModel):
    name: str


class OrganizationOut(BaseModel):
    org_id: uuid.UUID
    name: str
    role: str | None = None


class InviteIn(BaseModel):
    email: EmailStr
    role: str

    @field_validator("role")
    @classmethod
    def role_allowed(cls, value: str) -> str:
        allowed = {"OWNER", "EDITOR", "MANAGER", "VIEWER"}
        if value not in allowed:
            raise ValueError("Invalid role")
        return value


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str


class OrgSettingsOut(BaseModel):
    org_id: uuid.UUID
    starting_cash: Decimal
    runway_alert_threshold_days: int
    vendor_concentration_threshold_pct: Decimal
    budget_variance_alert_threshold_pct: Decimal
    misc_growth_multiplier: Decimal
    anomaly_spike_multiplier: Decimal
    owner_mfa_required: bool
    owner_session_max_minutes: int
    sensitive_action_reauth_minutes: int
    workforce_org_context_canonical: bool = True


class OrgSettingsUpdateIn(BaseModel):
    starting_cash: Decimal | None = None
    runway_alert_threshold_days: int | None = None
    vendor_concentration_threshold_pct: Decimal | None = None
    budget_variance_alert_threshold_pct: Decimal | None = None
    misc_growth_multiplier: Decimal | None = None
    anomaly_spike_multiplier: Decimal | None = None
    owner_mfa_required: bool | None = None
    owner_session_max_minutes: int | None = None
    sensitive_action_reauth_minutes: int | None = None
    workforce_org_context_canonical: bool | None = None

    @field_validator("starting_cash")
    @classmethod
    def validate_starting_cash(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if value < 0:
            raise ValueError("starting_cash must be >= 0")
        return value

    @field_validator("runway_alert_threshold_days")
    @classmethod
    def validate_runway_threshold(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 1 or value > 3650:
            raise ValueError("runway_alert_threshold_days must be between 1 and 3650")
        return value

    @field_validator("vendor_concentration_threshold_pct")
    @classmethod
    def validate_vendor_threshold(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if value < Decimal("1") or value > Decimal("100"):
            raise ValueError("vendor_concentration_threshold_pct must be between 1 and 100")
        return value

    @field_validator("budget_variance_alert_threshold_pct")
    @classmethod
    def validate_budget_variance_threshold(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if value < Decimal("1") or value > Decimal("1000"):
            raise ValueError("budget_variance_alert_threshold_pct must be between 1 and 1000")
        return value

    @field_validator("misc_growth_multiplier", "anomaly_spike_multiplier")
    @classmethod
    def validate_multipliers(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if value <= Decimal("1") or value > Decimal("10"):
            raise ValueError("multiplier must be > 1 and <= 10")
        return value

    @field_validator("owner_session_max_minutes", "sensitive_action_reauth_minutes")
    @classmethod
    def validate_security_window_minutes(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 5 or value > 1440:
            raise ValueError("minutes must be between 5 and 1440")
        return value


class PlanUsageMetricOut(BaseModel):
    used: int
    limit: int


class PlanUsageOut(BaseModel):
    plan_code: str
    period_start: str
    metrics: dict[str, PlanUsageMetricOut]


class OrgBillingOut(BaseModel):
    org_id: uuid.UUID
    billing_email: str | None
    invoice_enabled: bool
    plan_label: str
    billing_notes: str | None
    provider: str
    customer_id: str | None
    subscription_id: str | None
    subscription_status: str | None
    current_period_end: str | None
    active_price_id: str | None
    publishable_key: str | None = None


class OrgBillingUpdateIn(BaseModel):
    billing_email: EmailStr | None = None
    invoice_enabled: bool | None = None
    plan_label: str | None = None
    billing_notes: str | None = None


class OrgDeletionRequestIn(BaseModel):
    reason: str | None = None

