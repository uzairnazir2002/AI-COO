#!/usr/bin/env python
from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from datetime import date
from urllib.parse import urlparse, urlunparse

import asyncpg
import httpx


def _normalize_db_url(raw: str | None) -> str:
    db_url = raw or "postgresql://ai_coo:ai_coo@localhost:5432/ai_coo"
    db_url = db_url.replace("+asyncpg", "")
    parsed = urlparse(db_url)
    host = parsed.hostname or "localhost"
    if host in {"postgres", "db"}:
        netloc = parsed.netloc.replace(host, "localhost")
        parsed = parsed._replace(netloc=netloc)
        db_url = urlunparse(parsed)
    return db_url


async def _fetch_confirmation_token(email: str) -> str:
    db_url = _normalize_db_url(os.getenv("PERF_DATABASE_URL") or os.getenv("DATABASE_URL"))
    conn = await asyncpg.connect(dsn=db_url)
    try:
        for _ in range(25):
            body = await conn.fetchval(
                """
                SELECT payload->>'body'
                FROM outbox_events
                WHERE event_type='email.send'
                  AND payload->>'to'=$1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                email.lower(),
            )
            if body:
                match = re.search(r"token:\s*\n([A-Za-z0-9_\-]+)", body)
                if match:
                    return match.group(1)
            await asyncio.sleep(0.2)
    finally:
        await conn.close()
    raise RuntimeError("Unable to fetch confirmation token from outbox_events")


def main() -> None:
    base = "http://localhost:8000/api/v1"
    email = f"perf_{uuid.uuid4().hex[:10]}@example.com"
    password = "Password123!"

    with httpx.Client(timeout=30.0) as client:
        reg = client.post(f"{base}/auth/register", json={"email": email, "password": password})
        reg.raise_for_status()

        confirm_token = asyncio.run(_fetch_confirmation_token(email))
        confirm = client.post(f"{base}/auth/confirm", json={"token": confirm_token})
        confirm.raise_for_status()

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
