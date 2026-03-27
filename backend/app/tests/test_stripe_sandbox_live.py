import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import date, timedelta

import httpx
import pytest
import stripe


pytestmark = pytest.mark.integration


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        pytest.skip(f"Missing required env: {name}")
    return value


def _sign(payload: str, secret: str) -> str:
    ts = int(time.time())
    message = f"{ts}.{payload}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def _create_test_charge(secret_key: str, org_id: str):
    stripe.api_key = secret_key
    return stripe.Charge.create(
        amount=1575,
        currency="usd",
        source="tok_visa",
        description="AI COO live Stripe integration test",
        metadata={"org_id": org_id},
    )


def _wait_for_charge_event(secret_key: str, charge_id: str):
    stripe.api_key = secret_key
    deadline = time.time() + 45
    while time.time() < deadline:
        events = stripe.Event.list(type="charge.succeeded", limit=25)
        for event in events.auto_paging_iter():
            obj = getattr(event.data, "object", None)
            if obj and getattr(obj, "id", None) == charge_id:
                return event
        time.sleep(1.5)
    raise AssertionError(f"Timed out waiting for charge.succeeded event for charge {charge_id}")


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION_LIVE") != "1", reason="Set RUN_INTEGRATION_LIVE=1")
@pytest.mark.skipif(os.getenv("STRIPE_SANDBOX_E2E") != "1", reason="Set STRIPE_SANDBOX_E2E=1")
def test_live_stripe_sandbox_webhook_flow():
    base = os.getenv("INTEGRATION_BASE_URL", "http://localhost:8000/api/v1")
    stripe_secret_key = _required_env("STRIPE_SECRET_KEY")
    stripe_webhook_secret = _required_env("STRIPE_WEBHOOK_SECRET")
    email = f"stripe_it_{uuid.uuid4().hex[:12]}@example.com"
    password = "Password123!"

    with httpx.Client(timeout=45.0) as client:
        reg = client.post(f"{base}/auth/register", json={"email": email, "password": password})
        assert reg.status_code in {200, 409}, reg.text
        confirm_lookup = client.get(f"{base}/auth/dev/confirmation-token", params={"email": email})
        assert confirm_lookup.status_code == 200, confirm_lookup.text
        token = (confirm_lookup.json() or {}).get("token")
        assert token, "missing confirmation token for integration user"
        confirm = client.post(f"{base}/auth/confirm", json={"token": token})
        assert confirm.status_code == 200, confirm.text
        login = client.post(f"{base}/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        access_token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        org = client.post(f"{base}/organizations", headers=headers, json={"name": f"Stripe IT Org {date.today().isoformat()}"})
        assert org.status_code == 200, org.text
        org_id = org.json()["org_id"]

        connect = client.post(
            f"{base}/integrations/payments/stripe/connect",
            headers=headers,
            json={"org_id": org_id, "account_label": "Stripe Sandbox IT"},
        )
        assert connect.status_code == 200, connect.text

        list_connections = client.get(f"{base}/integrations/payments/connections", headers=headers, params={"org_id": org_id})
        assert list_connections.status_code == 200, list_connections.text
        assert len(list_connections.json()) >= 1

        charge = _create_test_charge(stripe_secret_key, org_id)
        event = _wait_for_charge_event(stripe_secret_key, charge.id)
        payload_dict = event.to_dict_recursive()
        payload_json = json.dumps(payload_dict, separators=(",", ":"))
        signature = _sign(payload_json, stripe_webhook_secret)

        webhook = client.post(
            f"{base}/integrations/payments/stripe/webhook",
            content=payload_json.encode("utf-8"),
            headers={"Content-Type": "application/json", "Stripe-Signature": signature},
        )
        assert webhook.status_code == 200, webhook.text
        body = webhook.json()
        assert body["ok"] is True
        assert body["status"] in {"PROCESSED", "DUPLICATE"}

        date_to = date.today()
        date_from = date_to - timedelta(days=7)
        recon = client.get(
            f"{base}/integrations/payments/reconciliation",
            headers=headers,
            params={
                "org_id": org_id,
                "provider": "STRIPE",
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
            },
        )
        assert recon.status_code == 200, recon.text
        recon_json = recon.json()
        assert int(recon_json["processor"]["entry_count"]) >= 1
