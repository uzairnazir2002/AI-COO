from __future__ import annotations

import argparse
import os
import uuid
from datetime import date, timedelta

import httpx


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
    *,
    base_url: str,
    auth_mode: str,
    csrf_cookie_name: str,
    csrf_header_name: str,
    seeded_email: str | None,
    seeded_password: str | None,
    seeded_org_id: str | None,
    as_of: str | None,
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
            if auth_mode == "bearer":
                token = register.json().get("access_token")
                if not token:
                    raise RuntimeError("Bearer mode expected access_token on register response")

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

        if as_of is None:
            as_of = date.today().isoformat()

        intel = client.get(
            f"{base_url}/workforce/intelligence/dashboard",
            headers=auth_headers,
            params={"org_id": org_id, "as_of": as_of},
        )
        intel.raise_for_status()
        payload = intel.json()

        print("OK workforce intelligence dashboard")
        print(f"org_id={payload.get('org_id')}")
        print(f"as_of={payload.get('as_of')}")
        print(f"top_risks={payload.get('top_risks')}")

        as_of_d = date.fromisoformat(str(payload.get("as_of") or as_of))
        rep_from = as_of_d - timedelta(days=29)
        rep = client.get(
            f"{base_url}/workforce/intelligence/reports/summary",
            headers=auth_headers,
            params={"org_id": org_id, "from": rep_from.isoformat(), "to": as_of_d.isoformat()},
        )
        rep.raise_for_status()
        rep_body = rep.json()
        print("OK workforce intelligence reports/summary")
        print(f"summary_lines_count={len(rep_body.get('summary_lines') or [])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test: Workforce Intelligence dashboard endpoint.")
    parser.add_argument("--base-url", default=os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000/api/v1"))
    parser.add_argument("--auth-mode", default=os.getenv("SMOKE_AUTH_MODE", "bearer"), choices=["bearer", "cookie"])
    parser.add_argument("--csrf-cookie-name", default=os.getenv("SMOKE_CSRF_COOKIE_NAME", "ai_coo_csrf_token"))
    parser.add_argument("--csrf-header-name", default=os.getenv("SMOKE_CSRF_HEADER_NAME", "X-CSRF-Token"))
    parser.add_argument("--seeded-email", default=os.getenv("SMOKE_USER_EMAIL"))
    parser.add_argument("--seeded-password", default=os.getenv("SMOKE_USER_PASSWORD"))
    parser.add_argument("--seeded-org-id", default=os.getenv("SMOKE_ORG_ID"))
    parser.add_argument("--as-of", default=os.getenv("SMOKE_AS_OF"))
    args = parser.parse_args()

    run(
        base_url=args.base_url,
        auth_mode=args.auth_mode,
        csrf_cookie_name=args.csrf_cookie_name,
        csrf_header_name=args.csrf_header_name,
        seeded_email=args.seeded_email,
        seeded_password=args.seeded_password,
        seeded_org_id=args.seeded_org_id,
        as_of=args.as_of,
    )


if __name__ == "__main__":
    main()

