from datetime import timedelta
from types import SimpleNamespace
import uuid

import pytest

from app.core.security import create_token
from app.domain.schemas.auth import TokenOut
from app.domain.services.auth_service import AuthService, UnauthorizedError, _h
from app.utils.time import utc_now


class _TokenSession:
    def __init__(self, user_id: uuid.UUID, refresh_hash: str):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.refresh_token_hash = refresh_hash
        self.expires_at = utc_now() + timedelta(days=1)
        self.is_revoked = False
        self.replaced_by_token_hash = None


class _User:
    def __init__(self, user_id: uuid.UUID, email: str, is_active: bool):
        self.id = user_id
        self.email = email
        self.is_active = is_active


class _FakeAuthRepo:
    def __init__(self):
        self.sessions = []
        self.refresh_lookup = {}
        self.users = {}

    async def create_token_session(
        self, user_id, refresh_token_hash, expires_at, user_agent, ip_address
    ):
        rec = _TokenSession(user_id, refresh_token_hash)
        rec.expires_at = expires_at
        rec.user_agent = user_agent
        rec.ip_address = ip_address
        self.sessions.append(rec)
        self.refresh_lookup[refresh_token_hash] = rec
        return rec

    async def get_token_session(self, refresh_token_hash: str):
        return self.refresh_lookup.get(refresh_token_hash)

    async def get_user(self, user_id: uuid.UUID):
        return self.users.get(user_id)

    async def revoke_token(self, token):
        token.is_revoked = True


class _FakeAuditRepo:
    async def log(self, *_args, **_kwargs):
        return None


class _FakeOrgRepo:
    pass


class _Req:
    def __init__(self):
        self.headers = {"user-agent": "pytest"}
        self.client = SimpleNamespace(host="127.0.0.1")


@pytest.mark.asyncio
async def test_issue_registration_tokens_creates_session_and_tokens():
    auth_repo = _FakeAuthRepo()
    svc = AuthService(auth_repo, _FakeOrgRepo(), _FakeAuditRepo(), None)  # type: ignore[arg-type]

    user_id = uuid.uuid4()
    token_out = await svc.issue_registration_tokens(user_id, _Req())

    assert isinstance(token_out, TokenOut)
    assert token_out.access_token
    assert token_out.refresh_token
    assert len(auth_repo.sessions) == 1
    assert auth_repo.sessions[0].user_id == user_id


@pytest.mark.asyncio
async def test_refresh_rejects_inactive_account_and_revokes_session():
    auth_repo = _FakeAuthRepo()
    svc = AuthService(auth_repo, _FakeOrgRepo(), _FakeAuditRepo(), None)  # type: ignore[arg-type]

    user_id = uuid.uuid4()
    refresh = create_token(str(user_id), "refresh", timedelta(days=1))
    session = _TokenSession(user_id, _h(refresh))
    session.expires_at = utc_now() + timedelta(days=1)
    auth_repo.refresh_lookup[_h(refresh)] = session
    auth_repo.users[user_id] = _User(user_id, "owner@example.com", is_active=False)

    with pytest.raises(UnauthorizedError):
        await svc.refresh(refresh, _Req())

    assert session.is_revoked is True
