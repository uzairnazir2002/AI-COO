from dataclasses import dataclass

from app.core.config import get_settings
from app.infra.cache import redis_client


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_ip(ip: str | None) -> str:
    return (ip or "unknown").strip().lower()


def _email_fail_key(email: str) -> str:
    return f"auth:lockout:fail:email:{_normalize_email(email)}"


def _ip_fail_key(ip: str | None) -> str:
    return f"auth:lockout:fail:ip:{_normalize_ip(ip)}"


def _scope_lock_key(email: str, ip: str | None) -> str:
    return f"auth:lockout:lock:{_normalize_email(email)}:{_normalize_ip(ip)}"


def _scope_escalation_key(email: str, ip: str | None) -> str:
    return f"auth:lockout:escalation:{_normalize_email(email)}:{_normalize_ip(ip)}"


@dataclass(slots=True)
class LockoutResult:
    locked: bool
    remaining_seconds: int
    failure_count: int
    escalation_level: int = 0
    escalated: bool = False


async def lockout_metrics() -> dict[str, int]:
    try:
        failures = int(await redis_client.get("auth:lockout:metric:failures") or 0)
        lockouts = int(await redis_client.get("auth:lockout:metric:lockouts") or 0)
        escalations = int(await redis_client.get("auth:lockout:metric:escalations") or 0)
        return {"failures_total": failures, "lockouts_total": lockouts, "escalations_total": escalations}
    except Exception:
        return {"failures_total": 0, "lockouts_total": 0, "escalations_total": 0}


async def is_locked(email: str, ip: str | None) -> LockoutResult:
    key = _scope_lock_key(email, ip)
    escalation_key = _scope_escalation_key(email, ip)
    try:
        ttl = int(await redis_client.ttl(key))
        locked = ttl > 0
        escalation_level = int(await redis_client.get(escalation_key) or 0)
        return LockoutResult(locked=locked, remaining_seconds=max(ttl, 0), failure_count=0, escalation_level=escalation_level)
    except Exception:
        return LockoutResult(locked=False, remaining_seconds=0, failure_count=0)


async def clear_login_failures(email: str, ip: str | None) -> None:
    try:
        await redis_client.delete(
            _scope_lock_key(email, ip),
            _scope_escalation_key(email, ip),
            _email_fail_key(email),
            _ip_fail_key(ip),
        )
    except Exception:
        return


async def record_login_failure(email: str, ip: str | None) -> LockoutResult:
    settings = get_settings()
    window_seconds = max(60, settings.auth_lockout_window_minutes * 60)
    lock_seconds = max(60, settings.auth_lockout_duration_minutes * 60)
    threshold = max(1, settings.auth_lockout_threshold)
    scope_key = _scope_lock_key(email, ip)
    escalation_key = _scope_escalation_key(email, ip)
    email_key = _email_fail_key(email)
    ip_key = _ip_fail_key(ip)
    try:
        await redis_client.incr("auth:lockout:metric:failures")
        count = int(await redis_client.incr(email_key))
        if count == 1:
            await redis_client.expire(email_key, window_seconds)
        ip_count = int(await redis_client.incr(ip_key))
        if ip_count == 1:
            await redis_client.expire(ip_key, window_seconds)
        escalation_level = max(0, min(3, count // threshold))
        prev_escalation_level = int(await redis_client.get(escalation_key) or 0)
        escalated = escalation_level > prev_escalation_level and escalation_level > 0
        if escalation_level > 0:
            await redis_client.set(escalation_key, str(escalation_level), ex=window_seconds)
        if escalated:
            await redis_client.incr("auth:lockout:metric:escalations")
        if count >= threshold:
            await redis_client.set(scope_key, "1", ex=lock_seconds)
            await redis_client.incr("auth:lockout:metric:lockouts")
            return LockoutResult(
                locked=True,
                remaining_seconds=lock_seconds,
                failure_count=count,
                escalation_level=escalation_level,
                escalated=escalated,
            )
        return LockoutResult(
            locked=False,
            remaining_seconds=0,
            failure_count=count,
            escalation_level=escalation_level,
            escalated=escalated,
        )
    except Exception:
        return LockoutResult(locked=False, remaining_seconds=0, failure_count=0)
