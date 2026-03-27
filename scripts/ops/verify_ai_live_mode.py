#!/usr/bin/env python
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
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


async def _fetch_confirmation_token(database_url: str, email: str, timeout_seconds: int = 12) -> str:
    conn = await asyncpg.connect(dsn=database_url)
    started_at = datetime.now(UTC)
    try:
        while (datetime.now(UTC) - started_at).total_seconds() < timeout_seconds:
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
            await asyncio.sleep(0.25)
    finally:
        await conn.close()
    raise RuntimeError("Unable to fetch confirmation token from outbox_events")


def _run_fallback_test(pytest_target: str) -> dict[str, object]:
    command = [sys.executable, "-m", "pytest", pytest_target, "-q"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "command": " ".join(command),
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "passed": result.returncode == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify live AI provider mode safely with API checks and fallback guard test.")
    parser.add_argument("--api-base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "postgresql://ai_coo:ai_coo@localhost:5432/ai_coo"))
    parser.add_argument("--email", default="")
    parser.add_argument("--password", default="Password123!")
    parser.add_argument("--org-name", default="AI Live Verify Org")
    parser.add_argument("--expected-provider", default="openai")
    parser.add_argument("--live-check", action="store_true")
    parser.add_argument("--verify-fallback-test", action="store_true")
    parser.add_argument(
        "--fallback-test-path",
        default="backend/app/tests/test_ai_service.py::test_ai_service_falls_back_on_provider_error",
    )
    parser.add_argument("--out-json", default="ai-live-mode-report.json")
    args = parser.parse_args()

    email = args.email or f"ai_live_verify_{uuid.uuid4().hex[:10]}@example.com"
    report: dict[str, object] = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "api_base_url": args.api_base_url.rstrip("/"),
        "email": email,
        "steps": [],
        "success": False,
    }

    try:
        db_url = _normalize_db_url(args.database_url)
        today = date.today().isoformat()
        month_start = date.today().replace(day=1).isoformat()
        base = args.api_base_url.rstrip("/")
        with httpx.Client(timeout=30.0) as client:
            reg = client.post(f"{base}/auth/register", json={"email": email, "password": args.password})
            reg.raise_for_status()
            report["steps"].append({"name": "register", "status": "ok"})

            token = asyncio.run(_fetch_confirmation_token(db_url, email))
            confirm = client.post(f"{base}/auth/confirm", json={"token": token})
            confirm.raise_for_status()
            report["steps"].append({"name": "confirm", "status": "ok"})

            login = client.post(f"{base}/auth/login", json={"email": email, "password": args.password})
            login.raise_for_status()
            access_token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            report["steps"].append({"name": "login", "status": "ok"})

            org_resp = client.post(f"{base}/organizations", json={"name": args.org_name}, headers=headers)
            org_resp.raise_for_status()
            org_id = org_resp.json()["org_id"]
            report["steps"].append({"name": "create_org", "status": "ok", "org_id": org_id})

            health = client.get(
                f"{base}/ai/health",
                params={"org_id": org_id, "live_check": str(args.live_check).lower()},
                headers=headers,
            )
            health.raise_for_status()
            health_payload = health.json()
            report["steps"].append({"name": "ai_health", "status": "ok", "payload": health_payload})

            provider = health_payload.get("provider", {})
            expected_provider = (args.expected_provider or "").strip().lower()
            if provider.get("provider") != expected_provider:
                raise RuntimeError(f"Expected provider={expected_provider}, got {provider.get('provider')}")
            if not provider.get("configured"):
                raise RuntimeError("AI provider reported configured=false")
            if not provider.get("healthy"):
                raise RuntimeError(f"AI provider reported healthy=false reason={provider.get('reason')}")
            if args.live_check and not provider.get("live_check_performed"):
                raise RuntimeError("AI provider live check was requested but not performed")
            if not health_payload.get("fallback_ready"):
                raise RuntimeError("AI fallback readiness is false")

            summary = client.post(
                f"{base}/ai/summary",
                headers=headers,
                json={"org_id": org_id, "from": month_start, "to": today},
            )
            summary.raise_for_status()
            summary_payload = summary.json()
            if "summary_json" not in summary_payload or "fallback_used" not in summary_payload:
                raise RuntimeError("Unexpected /ai/summary payload shape")
            report["steps"].append({"name": "ai_summary", "status": "ok", "payload": summary_payload})

            if args.verify_fallback_test:
                fallback = _run_fallback_test(args.fallback_test_path)
                report["steps"].append({"name": "fallback_guard_test", "status": "ok" if fallback["passed"] else "failed", "result": fallback})
                if not fallback["passed"]:
                    raise RuntimeError("Fallback guard test failed")

        report["success"] = True
    except Exception as exc:
        report["error"] = str(exc)
        report["success"] = False
    finally:
        output = Path(args.out_json)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
