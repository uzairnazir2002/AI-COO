from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import date, timedelta
from pathlib import Path

import httpx
import time


def _mutating_headers(
    auth_mode: str,
    token: str | None,
    client: httpx.Client,
    csrf_cookie_name: str,
    csrf_header_name: str,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if auth_mode == "bearer":
        assert token, "Bearer auth requires access token"
        headers["Authorization"] = f"Bearer {token}"
        return headers
    csrf = client.cookies.get(csrf_cookie_name)
    if not csrf:
        raise RuntimeError("Missing CSRF cookie in cookie auth mode")
    headers[csrf_header_name] = csrf
    return headers


def run(
    base_url: str,
    csv_path: Path,
    auth_mode: str = "bearer",
    csrf_cookie_name: str = "ai_coo_csrf_token",
    csrf_header_name: str = "X-CSRF-Token",
    seeded_email: str | None = None,
    seeded_password: str | None = None,
    seeded_org_id: str | None = None,
) -> None:
    email = seeded_email or f"smoke_{uuid.uuid4().hex[:10]}@example.com"
    password = seeded_password or "Password123!"

    with httpx.Client(timeout=30.0) as client:
        token: str | None = None
        if seeded_email and seeded_password:
            login = client.post(f"{base_url}/auth/login", json={"email": email, "password": password})
            login.raise_for_status()
            if auth_mode == "bearer":
                token = login.json().get("access_token")
        else:
            register = client.post(f"{base_url}/auth/register", json={"email": email, "password": password})
            register.raise_for_status()
            # Fresh registrations may be unconfirmed; some backends issue tokens but still block
            # org-scoped APIs until the account is confirmed/active. This smoke suite auto-confirms
            # in development using the dev token endpoint, then logs in to obtain an active session.
            reg_json = register.json()
            if auth_mode == "bearer":
                token = reg_json.get("access_token")
                if not token:
                    raise RuntimeError("Bearer mode expected access_token on register response (unconfirmed accounts cannot login).")

        if auth_mode == "bearer" and not token:
            raise RuntimeError("Missing bearer access token after auth bootstrap")

        org_id = seeded_org_id
        if not org_id:
            org = client.post(
                f"{base_url}/organizations",
                headers=_mutating_headers(auth_mode, token, client, csrf_cookie_name, csrf_header_name),
                json={"name": "Smoke Org"},
            )
            if org.status_code == 401 and "Account is not active" in org.text and not (seeded_email and seeded_password):
                dev = client.get(f"{base_url}/auth/dev/confirmation-token", params={"email": email})
                dev.raise_for_status()
                token_value = dev.json().get("token")
                if not token_value:
                    raise RuntimeError("Dev confirmation token endpoint did not return token")
                confirm = client.post(f"{base_url}/auth/confirm", json={"token": token_value})
                confirm.raise_for_status()

                login = client.post(f"{base_url}/auth/login", json={"email": email, "password": password})
                login.raise_for_status()
                if auth_mode == "bearer":
                    token = login.json().get("access_token")
                    if not token:
                        raise RuntimeError("Bearer mode expected access_token after confirmation login")

                org = client.post(
                    f"{base_url}/organizations",
                    headers=_mutating_headers(auth_mode, token, client, csrf_cookie_name, csrf_header_name),
                    json={"name": "Smoke Org"},
                )

            org.raise_for_status()
            org_id = org.json()["org_id"]
        auth_headers = {"Authorization": f"Bearer {token}"} if auth_mode == "bearer" and token else {}

        mapping = {
            "date": "date",
            "amount": "amount",
            "type": "type",
            "category": "category",
            "vendor": "vendor",
            "notes": "notes",
        }
        with csv_path.open("rb") as f:
            preview = client.post(
                f"{base_url}/transactions/import/csv",
                headers=_mutating_headers(auth_mode, token, client, csrf_cookie_name, csrf_header_name),
                data={"org_id": org_id, "mapping": json.dumps(mapping), "commit": "false"},
                files={"file": (csv_path.name, f, "text/csv")},
            )
            preview.raise_for_status()
        with csv_path.open("rb") as f:
            commit = client.post(
                f"{base_url}/transactions/import/csv",
                headers=_mutating_headers(auth_mode, token, client, csrf_cookie_name, csrf_header_name),
                data={"org_id": org_id, "mapping": json.dumps(mapping), "commit": "true"},
                files={"file": (csv_path.name, f, "text/csv")},
            )
            commit.raise_for_status()

        today = date.today()
        month_start = date(today.year, today.month, 1).isoformat()
        today_s = today.isoformat()
        summary = client.get(
            f"{base_url}/analytics/summary",
            headers=auth_headers,
            params={"org_id": org_id, "from": month_start, "to": today_s},
        )
        summary.raise_for_status()

        runway = client.get(
            f"{base_url}/runway",
            headers=auth_headers,
            params={"org_id": org_id, "lookback_months": 6, "conservative": "true"},
        )
        runway.raise_for_status()

        payroll_periods = client.get(
            f"{base_url}/workforce/payroll/periods",
            headers=auth_headers,
            params={"org_id": org_id, "limit": 10},
        )
        payroll_periods.raise_for_status()
        if not isinstance(payroll_periods.json(), list):
            raise RuntimeError("Expected payroll periods list response")

        payroll_employees = client.get(
            f"{base_url}/workforce/employees",
            headers=auth_headers,
            params={"org_id": org_id, "limit": 5000},
        )
        payroll_employees.raise_for_status()
        if not isinstance(payroll_employees.json(), list):
            raise RuntimeError("Expected workforce employees list response")

        leave_types = client.get(
            f"{base_url}/workforce/leave/types",
            headers=auth_headers,
            params={"org_id": org_id, "include_inactive": "true"},
        )
        leave_types.raise_for_status()
        if not isinstance(leave_types.json(), list):
            raise RuntimeError("Expected workforce leave types list response")

        attendance_daily = client.get(
            f"{base_url}/workforce/attendance/daily",
            headers=auth_headers,
            params={"org_id": org_id, "date": today_s},
        )
        attendance_daily.raise_for_status()
        ad_json = attendance_daily.json()
        if not isinstance(ad_json, dict) or "items" not in ad_json:
            raise RuntimeError("Expected workforce attendance daily response")

        announcements = client.get(
            f"{base_url}/workforce/announcements",
            headers=auth_headers,
            params={"org_id": org_id, "include_archived": "false"},
        )
        announcements.raise_for_status()
        if not isinstance(announcements.json(), list):
            raise RuntimeError("Expected workforce announcements list response")

        ann_templates = client.get(
            f"{base_url}/workforce/announcements/templates",
            headers=auth_headers,
            params={"org_id": org_id},
        )
        ann_templates.raise_for_status()
        if not isinstance(ann_templates.json(), list):
            raise RuntimeError("Expected workforce announcement templates list response")

        ann_keys = client.get(
            f"{base_url}/workforce/announcements/automation-keys",
            headers=auth_headers,
            params={"org_id": org_id},
        )
        ann_keys.raise_for_status()
        ak_json = ann_keys.json()
        if not isinstance(ak_json, dict) or "keys" not in ak_json or not isinstance(ak_json["keys"], list):
            raise RuntimeError("Expected workforce announcement automation-keys response")

        forecast = client.get(
            f"{base_url}/forecast",
            headers=auth_headers,
            params={"org_id": org_id, "months": 3},
        )
        forecast.raise_for_status()
        first_month = forecast.json()["scenarios"]["base"][0]["month"]
        override = client.post(
            f"{base_url}/forecast/override",
            headers=_mutating_headers(auth_mode, token, client, csrf_cookie_name, csrf_header_name),
            json={
                "org_id": org_id,
                "month": first_month,
                "scenario": "BASE",
                "revenue_override": 25000,
            },
        )
        override.raise_for_status()

        week_start = (today - timedelta(days=today.weekday() + 7)).isoformat()
        report_gen = client.post(
            f"{base_url}/reports/generate",
            headers=_mutating_headers(auth_mode, token, client, csrf_cookie_name, csrf_header_name),
            params={"org_id": org_id, "week_start": week_start},
        )
        report_gen.raise_for_status()
        report_id = report_gen.json().get("report_id")
        if not report_id:
            deadline = time.time() + 60
            while time.time() < deadline and not report_id:
                reports = client.get(f"{base_url}/reports", headers=auth_headers, params={"org_id": org_id})
                reports.raise_for_status()
                for item in reports.json().get("items", []):
                    if item.get("week_start") == week_start:
                        report_id = item.get("id")
                        break
                if not report_id:
                    time.sleep(2)

        if report_id:
            download = client.get(f"{base_url}/reports/{report_id}/download", headers=auth_headers, params={"org_id": org_id})
            download.raise_for_status()
            assert download.json()["url"], "Expected report download URL"
        else:
            raise RuntimeError("Report was enqueued but did not become available within timeout.")

        ai = client.post(
            f"{base_url}/ai/summary",
            headers=_mutating_headers(auth_mode, token, client, csrf_cookie_name, csrf_header_name),
            json={"org_id": org_id, "from": month_start, "to": today_s},
        )
        ai.raise_for_status()

        print("Smoke suite passed")
        print(f"User: {email}")
        print(f"Org: {org_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI COO MVP smoke suite.")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--auth-mode", choices=["bearer", "cookie"], default="bearer")
    parser.add_argument("--csrf-cookie-name", default="ai_coo_csrf_token")
    parser.add_argument("--csrf-header-name", default="X-CSRF-Token")
    parser.add_argument("--email", default=os.getenv("SMOKE_USER_EMAIL") or os.getenv("E2E_USER_EMAIL"))
    parser.add_argument("--password", default=os.getenv("SMOKE_USER_PASSWORD") or os.getenv("E2E_USER_PASSWORD"))
    parser.add_argument("--org-id", default=os.getenv("SMOKE_ORG_ID") or os.getenv("E2E_ORG_ID"))
    parser.add_argument(
        "--csv",
        default=str(Path(__file__).resolve().parents[1] / "shared" / "demo" / "transactions_6months.csv"),
    )
    args = parser.parse_args()
    run(
        args.base_url,
        Path(args.csv),
        auth_mode=args.auth_mode,
        csrf_cookie_name=args.csrf_cookie_name,
        csrf_header_name=args.csrf_header_name,
        seeded_email=args.email,
        seeded_password=args.password,
        seeded_org_id=args.org_id,
    )


if __name__ == "__main__":
    main()
