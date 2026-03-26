from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx

from app.core.config import Settings
from app.domain.services.errors import AppError


class BankProviderError(AppError):
    status_code = 502


@dataclass
class ProviderBankAccount:
    external_account_id: str
    name: str
    mask: str | None
    account_type: str | None
    account_subtype: str | None
    currency_code: str | None


@dataclass
class ProviderExchangeResult:
    access_token_ref: str
    external_item_id: str
    institution_id: str | None
    institution_name: str | None
    accounts: list[ProviderBankAccount]


@dataclass
class ProviderTransaction:
    external_transaction_id: str
    amount: Decimal
    posted_date: date
    currency_code: str | None
    name: str
    vendor: str | None
    category: str | None
    pending: bool = False


@dataclass
class ProviderSyncResult:
    next_cursor: str | None
    has_more: bool
    transactions: list[ProviderTransaction]


class BankProvider:
    async def create_link_token(self, *, org_id: str, user_id: str) -> dict:
        raise NotImplementedError

    async def exchange_public_token(self, *, public_token: str) -> ProviderExchangeResult:
        raise NotImplementedError

    async def sync_transactions(self, *, access_token_ref: str, cursor: str | None) -> ProviderSyncResult:
        raise NotImplementedError


class StubBankProvider(BankProvider):
    async def create_link_token(self, *, org_id: str, user_id: str) -> dict:
        expires_at = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
        return {
            "link_token": f"stub-link-{org_id[:8]}-{user_id[:8]}",
            "expiration": expires_at,
        }

    async def exchange_public_token(self, *, public_token: str) -> ProviderExchangeResult:
        seed = public_token.replace(" ", "-").lower()
        return ProviderExchangeResult(
            access_token_ref=f"stub-access-{seed}",
            external_item_id=f"stub-item-{seed}",
            institution_id="ins_stub",
            institution_name="Stub Bank",
            accounts=[
                ProviderBankAccount(
                    external_account_id=f"acct-checking-{seed}",
                    name="Checking",
                    mask="1234",
                    account_type="depository",
                    account_subtype="checking",
                    currency_code="USD",
                ),
                ProviderBankAccount(
                    external_account_id=f"acct-credit-{seed}",
                    name="Business Card",
                    mask="4242",
                    account_type="credit",
                    account_subtype="credit card",
                    currency_code="USD",
                ),
            ],
        )

    async def sync_transactions(self, *, access_token_ref: str, cursor: str | None) -> ProviderSyncResult:
        if cursor:
            return ProviderSyncResult(next_cursor=cursor, has_more=False, transactions=[])
        today = date.today()
        suffix = access_token_ref[-8:]
        txs = [
            ProviderTransaction(
                external_transaction_id=f"stub-tx-exp-{suffix}",
                amount=Decimal("150.25"),
                posted_date=today,
                currency_code="USD",
                name="Cloud Hosting",
                vendor="Stub Infra",
                category="Infrastructure",
            ),
            ProviderTransaction(
                external_transaction_id=f"stub-tx-rev-{suffix}",
                amount=Decimal("-980.00"),
                posted_date=today,
                currency_code="USD",
                name="Client Invoice Payment",
                vendor="Client A",
                category="Revenue",
            ),
        ]
        return ProviderSyncResult(next_cursor=f"stub-cursor-{suffix}", has_more=False, transactions=txs)


class PlaidBankProvider(BankProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = self._resolve_base_url(settings.plaid_env)

    @staticmethod
    def _resolve_base_url(env: str) -> str:
        normalized = (env or "sandbox").lower()
        if normalized == "sandbox":
            return "https://sandbox.plaid.com"
        if normalized == "development":
            return "https://development.plaid.com"
        return "https://production.plaid.com"

    def _auth_payload(self) -> dict:
        if not self.settings.plaid_client_id or not self.settings.plaid_secret:
            raise BankProviderError("Plaid credentials are not configured")
        return {"client_id": self.settings.plaid_client_id, "secret": self.settings.plaid_secret}

    async def _post(self, path: str, payload: dict) -> dict:
        timeout = httpx.Timeout(20.0)
        async with httpx.AsyncClient(timeout=timeout, base_url=self.base_url) as client:
            res = await client.post(path, json={**self._auth_payload(), **payload})
        if res.status_code >= 400:
            raise BankProviderError(f"Plaid API error ({res.status_code})")
        body = res.json()
        if body.get("error_code"):
            raise BankProviderError(f"Plaid API error ({body.get('error_code')})")
        return body

    async def create_link_token(self, *, org_id: str, user_id: str) -> dict:
        products = [p.strip() for p in self.settings.plaid_products.split(",") if p.strip()]
        countries = [c.strip() for c in self.settings.plaid_country_codes.split(",") if c.strip()]
        body = await self._post(
            "/link/token/create",
            {
                "client_name": "AI COO",
                "language": "en",
                "country_codes": countries or ["US"],
                "products": products or ["transactions"],
                "user": {"client_user_id": f"{org_id}:{user_id}"},
                "webhook": self.settings.plaid_webhook_url or None,
            },
        )
        return {"link_token": body["link_token"], "expiration": body.get("expiration")}

    async def exchange_public_token(self, *, public_token: str) -> ProviderExchangeResult:
        exchange = await self._post("/item/public_token/exchange", {"public_token": public_token})
        access_token = exchange["access_token"]
        item_id = exchange["item_id"]
        accounts = await self._post("/accounts/get", {"access_token": access_token})
        item = await self._post("/item/get", {"access_token": access_token})
        institution_id = item.get("item", {}).get("institution_id")
        institution_name = None
        if institution_id:
            try:
                inst = await self._post(
                    "/institutions/get_by_id",
                    {"institution_id": institution_id, "country_codes": ["US"], "options": {"include_optional_metadata": True}},
                )
                institution_name = inst.get("institution", {}).get("name")
            except Exception:
                institution_name = None
        mapped_accounts = [
            ProviderBankAccount(
                external_account_id=row["account_id"],
                name=row.get("name") or row.get("official_name") or "Bank Account",
                mask=row.get("mask"),
                account_type=row.get("type"),
                account_subtype=row.get("subtype"),
                currency_code=(row.get("balances", {}) or {}).get("iso_currency_code"),
            )
            for row in (accounts.get("accounts") or [])
        ]
        return ProviderExchangeResult(
            access_token_ref=access_token,
            external_item_id=item_id,
            institution_id=institution_id,
            institution_name=institution_name,
            accounts=mapped_accounts,
        )

    async def sync_transactions(self, *, access_token_ref: str, cursor: str | None) -> ProviderSyncResult:
        body = await self._post("/transactions/sync", {"access_token": access_token_ref, "cursor": cursor})
        txs = []
        for row in (body.get("added") or []):
            posted_at = row.get("authorized_date") or row.get("date")
            if not posted_at:
                continue
            category = None
            pfc = row.get("personal_finance_category") or {}
            if isinstance(pfc, dict):
                category = pfc.get("primary")
            txs.append(
                ProviderTransaction(
                    external_transaction_id=row["transaction_id"],
                    amount=Decimal(str(row.get("amount", "0"))),
                    posted_date=date.fromisoformat(str(posted_at)),
                    currency_code=row.get("iso_currency_code"),
                    name=row.get("name") or "Plaid Transaction",
                    vendor=row.get("merchant_name"),
                    category=category,
                    pending=bool(row.get("pending", False)),
                )
            )
        return ProviderSyncResult(
            next_cursor=body.get("next_cursor"),
            has_more=bool(body.get("has_more")),
            transactions=txs,
        )


def build_bank_provider(settings: Settings) -> BankProvider:
    if settings.bank_provider.lower() == "plaid":
        return PlaidBankProvider(settings)
    return StubBankProvider()


def verify_plaid_webhook_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature.strip().lower(), expected.lower())
