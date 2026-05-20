import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_token
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.auth_repo import AuthRepo
from app.domain.repos.org_repo import OrgRepo

bearer = HTTPBearer(auto_error=False)


@dataclass
class OrgContext:
    org_id: uuid.UUID
    role: str


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    settings = get_settings()
    token = creds.credentials if creds else None
    if not token and settings.auth_cookie_mode and request is not None:
        token = request.cookies.get(settings.access_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")
    if request is not None:
        request.state.auth_payload = payload
    repo = AuthRepo(db)
    user = await repo.get_user(uuid.UUID(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is not active")
    return user


async def get_org_context(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> OrgContext:
    repo = OrgRepo(db)
    membership = await repo.membership(user.id, org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Forbidden")
    role = str(membership.role)
    if role == "OWNER":
        settings = await repo.get_settings(org_id)
        if settings:
            if settings.owner_mfa_required and not user.mfa_enabled:
                raise HTTPException(status_code=403, detail="Owner MFA is required by organization policy")
            issued_at = None
            if request is not None:
                payload = getattr(request.state, "auth_payload", None)
                if isinstance(payload, dict) and isinstance(payload.get("iat"), int):
                    issued_at = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
            if issued_at is not None and settings.owner_session_max_minutes > 0:
                age_seconds = (datetime.now(tz=timezone.utc) - issued_at).total_seconds()
                if age_seconds > settings.owner_session_max_minutes * 60:
                    raise HTTPException(status_code=401, detail="Session expired by organization policy")
    return OrgContext(org_id=org_id, role=role)


def require_roles(*allowed: str):
    async def checker(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
        if ctx.role not in allowed:
            raise HTTPException(status_code=403, detail="Forbidden")
        return ctx

    return checker


def require_sensitive_reauth():
    async def checker(
        request: Request,
        org_id: uuid.UUID | None = None,
        user: User = Depends(get_current_user),
        ctx: object | None = None,
        db: AsyncSession = Depends(get_db),
    ) -> None:
        resolved_org_id = org_id
        if resolved_org_id is None and request is not None:
            q_org_id = request.query_params.get("org_id")
            if q_org_id:
                try:
                    resolved_org_id = uuid.UUID(q_org_id)
                except Exception as exc:
                    raise HTTPException(status_code=422, detail="Invalid org_id query") from exc
        if resolved_org_id is None and request is not None:
            try:
                payload = await request.json()
            except Exception:
                payload = None
            if isinstance(payload, dict):
                raw = payload.get("org_id")
                if raw:
                    try:
                        resolved_org_id = uuid.UUID(str(raw))
                    except Exception as exc:
                        raise HTTPException(status_code=422, detail="Invalid org_id body field") from exc
        resolved_org_id = resolve_org_id_from_request(resolved_org_id, request)
        resolved_ctx = ctx
        if resolved_ctx is None:
            if not hasattr(db, "execute"):
                return
            resolved_ctx = await get_org_context(org_id=resolved_org_id, user=user, request=request, db=db)
        if resolved_ctx.role != "OWNER":
            return
        settings = await OrgRepo(db).get_settings(resolved_org_id)
        if not settings or settings.sensitive_action_reauth_minutes <= 0:
            return
        payload = getattr(request.state, "auth_payload", None)
        issued_at_ts = payload.get("iat") if isinstance(payload, dict) else None
        if not isinstance(issued_at_ts, int):
            return
        issued_at = datetime.fromtimestamp(issued_at_ts, tz=timezone.utc)
        age_seconds = (datetime.now(tz=timezone.utc) - issued_at).total_seconds()
        if age_seconds <= settings.sensitive_action_reauth_minutes * 60:
            return
        token = request.headers.get("X-Reauth-Token")
        if not token:
            raise HTTPException(status_code=401, detail="Re-authentication is required for this action")
        payload = decode_token(token)
        if not payload or payload.get("type") != "reauth":
            raise HTTPException(status_code=401, detail="Invalid re-authentication token")
        if payload.get("sub") != str(user.id):
            raise HTTPException(status_code=401, detail="Invalid re-authentication token")
        if payload.get("org_id") != str(resolved_org_id):
            raise HTTPException(status_code=401, detail="Invalid re-authentication token")

    return checker


def resolve_org_id_from_request(org_id: uuid.UUID | None, request: Request | None) -> uuid.UUID:
    header_value = request.headers.get("X-Org-Id") if request is not None else None
    header_org_id: uuid.UUID | None = None
    if header_value:
        try:
            header_org_id = uuid.UUID(header_value)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Invalid X-Org-Id header") from exc
    if org_id is not None and header_org_id is not None and org_id != header_org_id:
        raise HTTPException(status_code=403, detail="org_id does not match request context")
    if header_org_id is not None:
        return header_org_id
    if org_id is not None:
        return org_id
    raise HTTPException(status_code=422, detail="org_id is required")


async def resolve_workforce_org_id_from_request(
    org_id: uuid.UUID | None,
    request: Request | None,
    db: AsyncSession,
) -> uuid.UUID:
    resolved_org_id = resolve_org_id_from_request(org_id, request)
    if not hasattr(db, "execute"):
        return resolved_org_id
    settings = await OrgRepo(db).get_settings(resolved_org_id)
    canonical_enabled = bool(getattr(settings, "workforce_org_context_canonical", False)) if settings else False
    if not canonical_enabled:
        return resolved_org_id
    header_value = request.headers.get("X-Org-Id") if request is not None else None
    if not header_value:
        raise HTTPException(status_code=422, detail="X-Org-Id header is required")
    try:
        header_org_id = uuid.UUID(header_value)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid X-Org-Id header") from exc
    if header_org_id != resolved_org_id:
        raise HTTPException(status_code=403, detail="org_id does not match request context")
    return header_org_id
