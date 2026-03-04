import os
import uuid
from datetime import date, timedelta

import httpx
import pytest


pytestmark = pytest.mark.integration


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION_LIVE") != "1", reason="Set RUN_INTEGRATION_LIVE=1")
def test_live_acceptance_flow():
    base = os.getenv("INTEGRATION_BASE_URL", "http://localhost:8000/api/v1")
    email = f"it_{uuid.uuid4().hex[:12]}@example.com"
    password = "Password123!"

    with httpx.Client(timeout=30.0) as client:
        reg = client.post(f"{base}/auth/register", json={"email": email, "password": password})
        assert reg.status_code == 200, reg.text

        login = client.post(f"{base}/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        login_json = login.json()
        token = login_json["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        org = client.post(f"{base}/organizations", headers=headers, json={"name": "Integration Org"})
        assert org.status_code == 200, org.text
        org_id = org.json()["org_id"]

        tx = client.post(
            f"{base}/transactions",
            headers=headers,
            json={
                "org_id": org_id,
                "date": date.today().isoformat(),
                "amount": "1000.00",
                "type": "REVENUE",
                "category": "Sales",
            },
        )
        assert tx.status_code == 200, tx.text

        tx_list = client.get(f"{base}/transactions", headers=headers, params={"org_id": org_id, "page": 1, "page_size": 20})
        assert tx_list.status_code == 200, tx_list.text
        assert tx_list.json()["total"] >= 1

        month_start = date.today().replace(day=1).isoformat()
        today = date.today().isoformat()

        summary = client.get(f"{base}/analytics/summary", headers=headers, params={"org_id": org_id, "from": month_start, "to": today})
        assert summary.status_code == 200, summary.text

        runway = client.get(f"{base}/runway", headers=headers, params={"org_id": org_id, "lookback_months": 6, "conservative": "false"})
        assert runway.status_code == 200, runway.text

        forecast = client.get(f"{base}/forecast", headers=headers, params={"org_id": org_id, "months": 3})
        assert forecast.status_code == 200, forecast.text
        fc = forecast.json()["scenarios"]
        assert len(fc["base"]) == 3

        alerts = client.get(f"{base}/alerts", headers=headers, params={"org_id": org_id, "status": "open"})
        assert alerts.status_code == 200, alerts.text

        week_start = (date.today() - timedelta(days=date.today().weekday() + 7)).isoformat()
        report_gen = client.post(f"{base}/reports/generate", headers=headers, params={"org_id": org_id, "week_start": week_start})
        assert report_gen.status_code == 200, report_gen.text

        reports = client.get(f"{base}/reports", headers=headers, params={"org_id": org_id})
        assert reports.status_code == 200, reports.text
        report_id = reports.json()["items"][0]["id"]

        report_dl = client.get(f"{base}/reports/{report_id}/download", headers=headers, params={"org_id": org_id})
        assert report_dl.status_code == 200, report_dl.text
        assert report_dl.json()["url"]

        ai = client.post(f"{base}/ai/summary", headers=headers, json={"org_id": org_id, "from": month_start, "to": today})
        assert ai.status_code == 200, ai.text
        ai_json = ai.json()
        assert "summary_json" in ai_json
        assert "fallback_used" in ai_json
