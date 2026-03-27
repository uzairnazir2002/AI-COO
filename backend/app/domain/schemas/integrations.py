import uuid
from datetime import datetime
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class PlaidLinkTokenIn(BaseModel):
    org_id: uuid.UUID


class PlaidLinkTokenOut(BaseModel):
    link_token: str
    expiration: str | None = None


class PlaidExchangeIn(BaseModel):
    org_id: uuid.UUID
    public_token: str = Field(min_length=1)
    institution_name: str | None = None


class BankAccountOut(BaseModel):
    id: uuid.UUID
    external_account_id: str
    name: str
    mask: str | None
    account_type: str | None
    account_subtype: str | None
    currency_code: str | None
    is_active: bool


class BankConnectionOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    provider: str
    status: str
    institution_id: str | None
    institution_name: str | None
    connected_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None
    accounts: list[BankAccountOut] = Field(default_factory=list)


class PlaidExchangeOut(BaseModel):
    connection: BankConnectionOut


class BankSyncEnqueueOut(BaseModel):
    job_id: str
    status: str
    connection_id: uuid.UUID


class StripeConnectIn(BaseModel):
    org_id: uuid.UUID
    provider_account_id: str | None = None
    account_label: str | None = None


class PaymentConnectionOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    provider: str
    status: str
    provider_account_id: str | None
    connected_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    metadata_json: dict = Field(default_factory=dict)


class StripeConnectOut(BaseModel):
    connection: PaymentConnectionOut


class PaymentTotalsOut(BaseModel):
    inflow: Decimal
    outflow: Decimal
    net: Decimal
    entry_count: int


class TransactionTotalsOut(BaseModel):
    revenue: Decimal
    expense: Decimal
    net: Decimal
    entry_count: int


class ReconciliationDeltaOut(BaseModel):
    net: Decimal
    absolute: Decimal


class PaymentReconciliationOut(BaseModel):
    org_id: uuid.UUID
    provider: str
    date_from: date
    date_to: date
    processor: PaymentTotalsOut
    transactions: TransactionTotalsOut
    delta: ReconciliationDeltaOut
