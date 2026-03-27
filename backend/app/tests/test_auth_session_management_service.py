from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import uuid

import pytest

from app.domain.services.auth_service import AuthService


class _FakeAuthRepo:
    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id
        self.s1 = SimpleNamespace(
            id=uuid.uuid4(),
            user_id=user_id,
            refresh_token_hash="h1",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            last_used_at=datetime.now(timezone.utc),
            user_agent="ua1",
            ip_address="127.0.0.1",
            is_revoked=False,
        )
        self.s2 = SimpleNamespace(
            id=uuid.uuid4(),
            user_id=user_id,
            refresh_token_hash="h2",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            last_used_at=datetime.now(timezone.utc),
            user_agent="ua2",
            ip_address="127.0.0.2",
            is_revoked=False,
        )

    async def list_sessions_for_user(self, user_id: uuid.UUID, include_revoked: bool = False):
        _ = include_revoked
        assert user_id == self.user_id
        return [self.s1, self.s2]

    async def get_token_session(self, refresh_hash: str):
        return self.s1 if refresh_hash == "h1" else None

    async def revoke_all_user_sessions(self, user_id: uuid.UUID, except_session_id=None):
        assert user_id == self.user_id
        if except_session_id == self.s1.id:
            self.s2.is_revoked = True
            return 1
        self.s1.is_revoked = True
        self.s2.is_revoked = True
        return 2


class _FakeAuditRepo:
    async def log(self, *_args, **_kwargs):
        return None


class _FakeOrgRepo:
    pass


@pytest.mark.asyncio
async def test_list_sessions_marks_current(monkeypatch):
    user_id = uuid.uuid4()
    repo = _FakeAuthRepo(user_id)
    svc = AuthService(repo, _FakeOrgRepo(), _FakeAuditRepo(), None)  # type: ignore[arg-type]

    monkeypatch.setattr("app.domain.services.auth_service._h", lambda token: token)

    rows = await svc.list_sessions(user_id=user_id, current_refresh_token="h1")

    assert len(rows) == 2
    assert rows[0].is_current is True
    assert rows[1].is_current is False


@pytest.mark.asyncio
async def test_revoke_other_sessions_keeps_current(monkeypatch):
    user_id = uuid.uuid4()
    repo = _FakeAuthRepo(user_id)
    svc = AuthService(repo, _FakeOrgRepo(), _FakeAuditRepo(), None)  # type: ignore[arg-type]

    monkeypatch.setattr("app.domain.services.auth_service._h", lambda token: token)

    revoked = await svc.revoke_other_sessions(user_id=user_id, current_refresh_token="h1")

    assert revoked == 1
    assert repo.s1.is_revoked is False
    assert repo.s2.is_revoked is True
