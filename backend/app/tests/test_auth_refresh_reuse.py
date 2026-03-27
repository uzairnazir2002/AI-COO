import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.domain.services.auth_service import AuthService, UnauthorizedError


class _Session:
    def __init__(self, user_id: uuid.UUID):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.is_revoked = False
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        self.replaced_by_token_hash = None


class _FakeAuthRepo:
    def __init__(self, session: _Session):
        self.session = session
        self.revoked_all_called = False
        self.created = []
        self.users = {session.user_id: SimpleNamespace(id=session.user_id, is_active=True)}

    async def get_token_session(self, _refresh_hash: str):
        return self.session

    async def rotate_token(self, token: _Session, replaced_by_token_hash: str):
        token.is_revoked = True
        token.replaced_by_token_hash = replaced_by_token_hash

    async def create_token_session(self, **kwargs):
        self.created.append(kwargs)
        return kwargs

    async def get_user(self, user_id: uuid.UUID):
        return self.users.get(user_id)

    async def revoke_all_user_sessions(self, user_id: uuid.UUID):
        assert user_id == self.session.user_id
        self.revoked_all_called = True
        return 1


class _FakeOrgRepo:
    pass


class _FakeAuditRepo:
    def __init__(self):
        self.actions: list[str] = []

    async def log(self, _actor_user_id, _org_id, action, _entity_type, _entity_id, _metadata):
        self.actions.append(action)


@pytest.mark.asyncio
async def test_refresh_rotation_still_works(monkeypatch):
    user_id = uuid.uuid4()
    session = _Session(user_id)
    auth_repo = _FakeAuthRepo(session)
    audit_repo = _FakeAuditRepo()
    svc = AuthService(auth_repo, _FakeOrgRepo(), audit_repo)  # type: ignore[arg-type]

    now_ts = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())

    def _decode(token: str):
        if token == "old-refresh":
            return {"sub": str(user_id), "type": "refresh", "exp": now_ts}
        if token == "new-refresh":
            return {"sub": str(user_id), "type": "refresh", "exp": now_ts}
        return None

    monkeypatch.setattr("app.domain.services.auth_service.decode_token", _decode)
    monkeypatch.setattr("app.domain.services.auth_service.create_token", lambda _sub, t, _ttl: f"new-{t}")

    request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
    out = await svc.refresh("old-refresh", request)

    assert out.access_token == "new-access"
    assert out.refresh_token == "new-refresh"
    assert session.is_revoked is True
    assert session.replaced_by_token_hash is not None
    assert auth_repo.revoked_all_called is False
    assert "auth.refresh" in audit_repo.actions


@pytest.mark.asyncio
async def test_refresh_reuse_triggers_session_revocation(monkeypatch):
    user_id = uuid.uuid4()
    session = _Session(user_id)
    session.is_revoked = True
    session.replaced_by_token_hash = "hash-of-new-token"
    auth_repo = _FakeAuthRepo(session)
    audit_repo = _FakeAuditRepo()
    svc = AuthService(auth_repo, _FakeOrgRepo(), audit_repo)  # type: ignore[arg-type]

    now_ts = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())
    monkeypatch.setattr(
        "app.domain.services.auth_service.decode_token",
        lambda _token: {"sub": str(user_id), "type": "refresh", "exp": now_ts},
    )

    request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
    with pytest.raises(UnauthorizedError):
        await svc.refresh("old-refresh", request)

    assert auth_repo.revoked_all_called is True
    assert "auth.refresh.reuse_detected" in audit_repo.actions
