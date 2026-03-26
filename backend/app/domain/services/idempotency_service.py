import uuid
from dataclasses import dataclass
from datetime import timedelta

from app.core.config import get_settings
from app.domain.repos.idempotency_repo import IdempotencyRepo
from app.domain.services.errors import ConflictError
from app.utils.time import utc_now


@dataclass(slots=True)
class ReplayResult:
    status_code: int
    response_json: dict


class IdempotencyService:
    def __init__(self, repo: IdempotencyRepo):
        self.repo = repo

    async def get_replay(
        self,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        endpoint: str,
        idempotency_key: str | None,
        request_hash: str,
    ) -> ReplayResult | None:
        if not idempotency_key:
            return None
        now = utc_now()
        existing = await self.repo.get_active(
            org_id=org_id,
            user_id=user_id,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
            now=now,
        )
        if not existing:
            return None
        if existing.request_hash != request_hash:
            raise ConflictError("Idempotency key was already used with different request data")
        return ReplayResult(status_code=existing.status_code, response_json=existing.response_json or {})

    async def store_response(
        self,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        endpoint: str,
        idempotency_key: str | None,
        request_hash: str,
        status_code: int,
        response_json: dict,
    ) -> None:
        if not idempotency_key:
            return
        settings = get_settings()
        expires_at = utc_now() + timedelta(hours=settings.idempotency_ttl_hours)
        await self.repo.upsert_completed(
            org_id=org_id,
            user_id=user_id,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            status_code=status_code,
            response_json=response_json,
            expires_at=expires_at,
        )
