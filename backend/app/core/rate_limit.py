from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.infra.cache import redis_client


async def enforce_auth_rate_limit(request: Request, action: str, per_minute: int | None = None) -> None:
    settings = get_settings()
    limit = per_minute or settings.rate_limit_per_minute
    ip = request.client.host if request.client else "unknown"
    key = f"rl:auth:{action}:{ip}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, 60)
        if count > limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    except HTTPException:
        raise
    except Exception:
        # Fail-open if Redis is unavailable to keep auth service reachable.
        return
