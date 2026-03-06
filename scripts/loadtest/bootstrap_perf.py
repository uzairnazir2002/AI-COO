#!/usr/bin/env python
from __future__ import annotations

import json
import uuid
from datetime import date

import httpx


def main() -> None:
    base = "http://localhost:8000/api/v1"
    email = f"perf_{uuid.uuid4().hex[:10]}@example.com"
    password = "Password123!"

    with httpx.Client(timeout=30.0) as client:
        reg = client.post(f"{base}/auth/register", json={"email": email, "password": password})
        reg.raise_for_status()

        login = client.post(f"{base}/auth/login", json={"email": email, "password": password})
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        org = client.post(f"{base}/organizations", json={"name": "Perf Org"}, headers=headers)
        org.raise_for_status()
        org_id = org.json()["org_id"]

        me = client.get(f"{base}/auth/me", headers=headers)
        me.raise_for_status()
        user_id = me.json()["user"]["id"]

        month_start = date.today().replace(day=1).isoformat()
        out = {
            "base_url": base,
            "email": email,
            "password": password,
            "access_token": token,
            "org_id": org_id,
            "user_id": user_id,
            "month_start": month_start,
            "today": date.today().isoformat(),
        }
        print(json.dumps(out))


if __name__ == "__main__":
    main()
