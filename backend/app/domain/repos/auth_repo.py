import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.account_confirmation_token import AccountConfirmationToken
from app.domain.models.membership import Membership
from app.domain.models.token_session import TokenSession
from app.domain.models.user import User


class AuthRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        q = await self.db.execute(select(User).where(User.email == email))
        return q.scalar_one_or_none()

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        q = await self.db.execute(select(User).where(User.id == user_id))
        return q.scalar_one_or_none()

    async def create_user(self, email: str, password_hash: str, is_active: bool = True) -> User:
        user = User(email=email.lower(), password_hash=password_hash, is_active=is_active)
        self.db.add(user)
        await self.db.flush()
        return user

    async def save_user(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        return user

    async def create_token_session(
        self,
        user_id: uuid.UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenSession:
        s = TokenSession(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(s)
        await self.db.flush()
        return s

    async def get_token_session(self, refresh_token_hash: str) -> TokenSession | None:
        q = await self.db.execute(
            select(TokenSession).where(TokenSession.refresh_token_hash == refresh_token_hash)
        )
        return q.scalar_one_or_none()

    async def revoke_token(self, token: TokenSession) -> None:
        token.is_revoked = True
        await self.db.flush()

    async def rotate_token(self, token: TokenSession, replaced_by_token_hash: str) -> None:
        token.is_revoked = True
        token.replaced_by_token_hash = replaced_by_token_hash
        await self.db.flush()

    async def revoke_all_user_sessions(self, user_id: uuid.UUID) -> int:
        q = await self.db.execute(select(TokenSession).where(TokenSession.user_id == user_id, TokenSession.is_revoked.is_(False)))
        sessions = list(q.scalars().all())
        for s in sessions:
            s.is_revoked = True
        await self.db.flush()
        return len(sessions)

    async def memberships_for_user(self, user_id: uuid.UUID) -> list[Membership]:
        q = await self.db.execute(select(Membership).where(Membership.user_id == user_id))
        return list(q.scalars().all())

    async def create_confirmation_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> AccountConfirmationToken:
        tok = AccountConfirmationToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(tok)
        await self.db.flush()
        return tok

    async def get_confirmation_token(self, token_hash: str) -> AccountConfirmationToken | None:
        q = await self.db.execute(
            select(AccountConfirmationToken).where(AccountConfirmationToken.token_hash == token_hash)
        )
        return q.scalar_one_or_none()

    async def mark_confirmation_token_used(self, token: AccountConfirmationToken) -> None:
        from app.utils.time import utc_now

        token.used_at = utc_now()
        await self.db.flush()
