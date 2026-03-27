from pydantic import BaseModel


class BillingCheckoutIn(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


class BillingCheckoutOut(BaseModel):
    url: str


class BillingPortalIn(BaseModel):
    return_url: str


class BillingPortalOut(BaseModel):
    url: str
