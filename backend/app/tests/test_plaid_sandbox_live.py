import os
import time
import uuid
from datetime import date

import httpx
import pytest


pytestmark = pytest.mark.integration


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        pytest.skip(f"Missing required env: {name}")
    return value


def _create_sandbox_public_token(*, client_id: str, secret: str) -> str:
    payload = {
        "client_id": client_id,
        "secret": secret,
        "institution_id": os.getenv("PLAID_TEST_INSTITUTION_ID", "ins_109508"),
        "initial_products": ["transactions"],
        "options": {"webhook": "https://example.com/plaid-test-webhook"},
    }
    with httpx.Client(timeout=30.0) as client:
        res = client.post("https://sandbox.plaid.com/sandbox/public_token/create", json=payload)
        res.raise_for_status()
        body = res.json()
        if not body.get("public_token"):
            raise RuntimeError(f"Plaid sandbox did not return public_token: {body}")
        return str(body["public_token"])


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION_LIVE") != "1", reason="Set RUN_INTEGRATION_LIVE=1")
@pytest.mark.skipif(os.getenv("PLAID_SANDBOX_E2E") != "1", reason="Set PLAID_SANDBOX_E2E=1")
def test_live_plaid_sandbox_integration_flow():
    base = os.getenv("INTEGRATION_BASE_URL", "http://localhost:8000/api/v1")
    client_id = _required_env("PLAID_CLIENT_ID")
    secret = _required_env("PLAID_SECRET")
    email = f"plaid_it_{uuid.uuid4().hex[:12]}@example.com"
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
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        org = client.post(f"{base}/organizations", headers=headers, json={"name": f"Plaid IT Org {date.today().isoformat()}"})
        assert org.status_code == 200, org.text
        org_id = org.json()["org_id"]

        public_token = _create_sandbox_public_token(client_id=client_id, secret=secret)

        exchange = client.post(
            f"{base}/integrations/banks/plaid/exchange",
            headers=headers,
            json={"org_id": org_id, "public_token": public_token, "institution_name": "Plaid Sandbox"},
        )
        assert exchange.status_code == 200, exchange.text
        connection_id = exchange.json()["connection"]["id"]

        list_connections = client.get(f"{base}/integrations/banks/connections", headers=headers, params={"org_id": org_id})
        assert list_connections.status_code == 200, list_connections.text
        assert any(item["id"] == connection_id for item in list_connections.json())

        sync = client.post(f"{base}/integrations/banks/{connection_id}/sync", headers=headers, params={"org_id": org_id})
        assert sync.status_code == 200, sync.text
        job_id = sync.json()["job_id"]

        deadline = time.time() + 90
        final_status = None
        while time.time() < deadline:
            jobs = client.get(f"{base}/jobs", headers=headers, params={"org_id": org_id, "page": 1, "page_size": 50})
            assert jobs.status_code == 200, jobs.text
            rows = jobs.json()["items"]
            row = next((j for j in rows if j["task_id"] == job_id), None)
            if row and row["status"] in {"SUCCEEDED", "FAILED"}:
                final_status = row["status"]
                break
            time.sleep(2.0)

        assert final_status == "SUCCEEDED", f"sync job did not succeed (status={final_status})"

        tx_list = client.get(
            f"{base}/transactions",
            headers=headers,
            params={"org_id": org_id, "page": 1, "page_size": 20},
        )
        assert tx_list.status_code == 200, tx_list.text
        assert tx_list.json()["total"] >= 1
