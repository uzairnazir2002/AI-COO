import uuid
from dataclasses import dataclass

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
    repo = AuthRepo(db)
    user = await repo.get_user(uuid.UUID(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_org_context(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrgContext:
    membership = await OrgRepo(db).membership(user.id, org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Forbidden")
    return OrgContext(org_id=org_id, role=str(membership.role))


def require_roles(*allowed: str):
    async def checker(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
        if ctx.role not in allowed:
            raise HTTPException(status_code=403, detail="Forbidden")
        return ctx

    return checker
