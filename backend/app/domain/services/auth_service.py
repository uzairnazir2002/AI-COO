import hashlib
import uuid
from datetime import timezone

from fastapi import Request

from app.core.security import access_ttl, create_token, decode_token, hash_password, refresh_ttl, verify_password
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.auth_repo import AuthRepo
from app.domain.repos.org_repo import OrgRepo
from app.domain.schemas.auth import TokenOut
from app.domain.services.errors import ConflictError, UnauthorizedError
from app.utils.time import utc_now


def _h(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, auth_repo: AuthRepo, org_repo: OrgRepo, audit_repo: AuditRepo):
        self.auth_repo = auth_repo
        self.org_repo = org_repo
        self.audit_repo = audit_repo

    async def register(self, email: str, password: str):
        existing = await self.auth_repo.get_user_by_email(email.lower())
        if existing:
            raise ConflictError("Email already exists")
        user = await self.auth_repo.create_user(email=email, password_hash=hash_password(password))
        await self.audit_repo.log(user.id, None, "auth.register", "user", str(user.id), {"email": email})
        return user

    async def login(self, email: str, password: str, request: Request) -> TokenOut:
        user = await self.auth_repo.get_user_by_email(email.lower())
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")
        refresh = create_token(str(user.id), "refresh", refresh_ttl())
        access = create_token(str(user.id), "access", access_ttl())
        refresh_payload = decode_token(refresh) or {}
        exp = utc_now().replace(tzinfo=timezone.utc)
        exp = exp.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        await self.auth_repo.create_token_session(
            user_id=user.id,
            refresh_token_hash=_h(refresh),
            expires_at=exp,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        await self.audit_repo.log(user.id, None, "auth.login", "user", str(user.id), {})
        return TokenOut(access_token=access, refresh_token=refresh, expires_in=int(access_ttl().total_seconds()))

    async def refresh(self, refresh_token: str, request: Request) -> TokenOut:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid refresh token")
        session = await self.auth_repo.get_token_session(_h(refresh_token))
        now = utc_now()
        if not session or session.is_revoked or session.expires_at <= now:
            raise UnauthorizedError("Refresh revoked")
        await self.auth_repo.revoke_token(session)
        user_id = uuid.UUID(payload["sub"])
        access = create_token(str(user_id), "access", access_ttl())
        new_refresh = create_token(str(user_id), "refresh", refresh_ttl())
        p2 = decode_token(new_refresh) or {}
        await self.auth_repo.create_token_session(
            user_id=user_id,
            refresh_token_hash=_h(new_refresh),
            expires_at=utc_now().fromtimestamp(p2["exp"], tz=timezone.utc),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        await self.audit_repo.log(user_id, None, "auth.refresh", "user", str(user_id), {})
        return TokenOut(access_token=access, refresh_token=new_refresh, expires_in=int(access_ttl().total_seconds()))

    async def logout(self, refresh_token: str, user_id: uuid.UUID | None) -> None:
        session = await self.auth_repo.get_token_session(_h(refresh_token))
        if session:
            await self.auth_repo.revoke_token(session)
        await self.audit_repo.log(user_id, None, "auth.logout", "token_session", str(user_id or "anonymous"), {})

    async def accept_invite(self, token: str, password: str):
        invite = await self.org_repo.get_invite_by_hash(_h(token))
        now = utc_now()
        if not invite or invite.accepted_at is not None or invite.expires_at <= now:
            raise UnauthorizedError("Invalid or expired invite token")
        user = await self.auth_repo.get_user_by_email(invite.email)
        if user:
            user.password_hash = hash_password(password)
            user.is_active = True
            await self.auth_repo.save_user(user)
        else:
            user = await self.auth_repo.create_user(invite.email, hash_password(password), is_active=True)
        membership = await self.org_repo.membership(user.id, invite.org_id)
        if not membership:
            await self.org_repo.add_membership(user.id, invite.org_id, invite.role)
        invite.accepted_at = now
        await self.audit_repo.log(
            user.id,
            invite.org_id,
            "org.invite.accept",
            "organization_invite",
            str(invite.id),
            {"role": invite.role},
        )
        return user
