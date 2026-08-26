import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.account_confirmation_token import AccountConfirmationToken
from app.domain.models.membership import Membership
from app.domain.models.token_session import TokenSession
from app.domain.models.user import User
from app.core.pii_crypto import pii_encrypt
from app.utils.time import utc_now


class AuthRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        q = await self.db.execute(select(User).where(User.email == email, User.deleted_at.is_(None)))
        return q.scalar_one_or_none()

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        q = await self.db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
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
            user_agent=pii_encrypt(user_agent),
            ip_address=pii_encrypt(ip_address),
            last_used_at=utc_now(),
        )
        self.db.add(s)
        await self.db.flush()
        return s

    async def get_token_session(self, refresh_token_hash: str) -> TokenSession | None:
        q = await self.db.execute(
            select(TokenSession).where(TokenSession.refresh_token_hash == refresh_token_hash)
        )
        return q.scalar_one_or_none()

    async def get_session_by_id(self, session_id: uuid.UUID, user_id: uuid.UUID) -> TokenSession | None:
        q = await self.db.execute(select(TokenSession).where(TokenSession.id == session_id, TokenSession.user_id == user_id))
        return q.scalar_one_or_none()

    async def list_sessions_for_user(self, user_id: uuid.UUID, *, include_revoked: bool = False) -> list[TokenSession]:
        q = select(TokenSession).where(TokenSession.user_id == user_id)
        if not include_revoked:
            q = q.where(TokenSession.is_revoked.is_(False))
        q = q.order_by(TokenSession.created_at.desc())
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def revoke_session(self, session: TokenSession) -> None:
        session.is_revoked = True
        await self.db.flush()

    async def revoke_token(self, token: TokenSession) -> None:
        token.is_revoked = True
        await self.db.flush()

    async def touch_session(self, token: TokenSession) -> None:
        token.last_used_at = utc_now()
        await self.db.flush()

    async def rotate_token(self, token: TokenSession, replaced_by_token_hash: str) -> None:
        token.is_revoked = True
        token.replaced_by_token_hash = replaced_by_token_hash
        token.last_used_at = utc_now()
        await self.db.flush()

    async def revoke_all_user_sessions(self, user_id: uuid.UUID, except_session_id: uuid.UUID | None = None) -> int:
        q = await self.db.execute(select(TokenSession).where(TokenSession.user_id == user_id, TokenSession.is_revoked.is_(False)))
        sessions = list(q.scalars().all())
        revoked = 0
        for s in sessions:
            if except_session_id and s.id == except_session_id:
                continue
            s.is_revoked = True
            revoked += 1
        await self.db.flush()
        return revoked

    async def memberships_for_user(self, user_id: uuid.UUID) -> list[Membership]:
        q = await self.db.execute(select(Membership).where(Membership.user_id == user_id))
        return list(q.scalars().all())

    async def create_confirmation_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        *,
        code_hash: str | None = None,
        code_expires_at: datetime | None = None,
        code_max_attempts: int = 5,
    ) -> AccountConfirmationToken:
        tok = AccountConfirmationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            code_hash=code_hash,
            code_expires_at=code_expires_at,
            code_attempts=0,
            code_max_attempts=code_max_attempts,
            invalidated_at=None,
        )
        self.db.add(tok)
        await self.db.flush()
        return tok

    async def get_confirmation_token(self, token_hash: str) -> AccountConfirmationToken | None:
        q = await self.db.execute(
            select(AccountConfirmationToken).where(AccountConfirmationToken.token_hash == token_hash)
        )
        return q.scalar_one_or_none()

    async def get_pending_confirmation_token_for_user(self, user_id: uuid.UUID) -> AccountConfirmationToken | None:
        q = await self.db.execute(
            select(AccountConfirmationToken)
            .where(
                AccountConfirmationToken.user_id == user_id,
                AccountConfirmationToken.used_at.is_(None),
                AccountConfirmationToken.invalidated_at.is_(None),
            )
            .order_by(AccountConfirmationToken.created_at.desc())
        )
        return q.scalars().first()

    async def get_confirmation_token_by_code_hash_for_user(
        self,
        *,
        user_id: uuid.UUID,
        code_hash: str,
    ) -> AccountConfirmationToken | None:
        q = await self.db.execute(
            select(AccountConfirmationToken)
            .where(
                AccountConfirmationToken.user_id == user_id,
                AccountConfirmationToken.code_hash == code_hash,
                AccountConfirmationToken.used_at.is_(None),
                AccountConfirmationToken.invalidated_at.is_(None),
            )
            .order_by(AccountConfirmationToken.created_at.desc())
        )
        return q.scalars().first()

    async def invalidate_unused_confirmation_tokens(self, user_id: uuid.UUID) -> int:
        tokens_q = await self.db.execute(
            select(AccountConfirmationToken).where(
                AccountConfirmationToken.user_id == user_id,
                AccountConfirmationToken.used_at.is_(None),
                AccountConfirmationToken.invalidated_at.is_(None),
            )
        )
        rows = list(tokens_q.scalars().all())
        now = utc_now()
        for row in rows:
            row.invalidated_at = now
        await self.db.flush()
        return len(rows)

    async def increment_confirmation_code_attempts(self, token: AccountConfirmationToken) -> None:
        token.code_attempts = int(token.code_attempts or 0) + 1
        await self.db.flush()

    async def mark_confirmation_token_used(self, token: AccountConfirmationToken) -> None:
        from app.utils.time import utc_now

        token.used_at = utc_now()
        await self.db.flush()
