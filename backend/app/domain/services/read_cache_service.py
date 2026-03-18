from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date

from app.infra.cache import redis_client


def alerts_cache_key(org_id: uuid.UUID, status: str | None) -> str:
    normalized = (status or "all").strip().lower()
    return f"cache:v1:alerts:{org_id}:{normalized}"


def alerts_cache_prefix(org_id: uuid.UUID) -> str:
    return f"cache:v1:alerts:{org_id}:"


def analytics_summary_cache_key(org_id: uuid.UUID, from_date: date, to_date: date) -> str:
    return f"cache:v1:analytics:summary:{org_id}:{from_date.isoformat()}:{to_date.isoformat()}"


def analytics_summary_cache_prefix(org_id: uuid.UUID) -> str:
    return f"cache:v1:analytics:summary:{org_id}:"


def transactions_cache_key(
    org_id: uuid.UUID,
    from_date: date | None,
    to_date: date | None,
    tx_type: str | None,
    category: str | None,
    q: str | None,
    page: int,
    page_size: int,
) -> str:
    payload = {
        "org_id": str(org_id),
        "from": from_date.isoformat() if from_date else None,
        "to": to_date.isoformat() if to_date else None,
        "type": tx_type,
        "category": category,
        "q": q,
        "page": page,
        "page_size": page_size,
    }
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"cache:v1:transactions:{org_id}:{digest}"


def transactions_cache_prefix(org_id: uuid.UUID) -> str:
    return f"cache:v1:transactions:{org_id}:"


async def cache_get_json(key: str) -> dict | list | None:
    try:
        value = await redis_client.get(key)
        if not value:
            return None
        return json.loads(value)
    except Exception:
        return None


async def cache_set_json(key: str, payload: dict | list, ttl_seconds: int) -> None:
    try:
        await redis_client.set(key, json.dumps(payload), ex=max(ttl_seconds, 1))
    except Exception:
        return


async def cache_delete_prefix(prefix: str) -> None:
    try:
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor=cursor, match=f"{prefix}*", count=200)
            if keys:
                await redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        return
