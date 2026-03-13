#!/usr/bin/env python
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import uuid
from datetime import date
from urllib.parse import urlparse, urlunparse

import asyncpg


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap one user with many orgs for scalability profiles.")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--org-count", type=int, default=10)
    parser.add_argument("--org-name-prefix", default="Perf Org")
    parser.add_argument("--password", default="Password123!")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    import httpx

    email = f"perf_multi_{uuid.uuid4().hex[:10]}@example.com"

    with httpx.Client(timeout=30.0) as client:
        reg = client.post(f"{args.base_url}/auth/register", json={"email": email, "password": args.password})
        reg.raise_for_status()

        confirm_token = asyncio.run(_fetch_confirmation_token(email))
        confirm = client.post(f"{args.base_url}/auth/confirm", json={"token": confirm_token})
        confirm.raise_for_status()

        login = client.post(f"{args.base_url}/auth/login", json={"email": email, "password": args.password})
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get(f"{args.base_url}/auth/me", headers=headers)
        me.raise_for_status()
        user_id = me.json()["user"]["id"]

        org_ids: list[str] = []
        for idx in range(args.org_count):
            org_name = f"{args.org_name_prefix} {idx + 1}"
            org_resp = client.post(f"{args.base_url}/organizations", json={"name": org_name}, headers=headers)
            org_resp.raise_for_status()
            org_ids.append(org_resp.json()["org_id"])

        month_start = date.today().replace(day=1).isoformat()
        out = {
            "base_url": args.base_url,
            "email": email,
            "password": args.password,
            "access_token": token,
            "user_id": user_id,
            "org_ids": org_ids,
            "month_start": month_start,
            "today": date.today().isoformat(),
        }
        print(json.dumps(out))


if __name__ == "__main__":
    main()
