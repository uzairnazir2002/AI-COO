from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request


def _request_with_iat(iat_ts: int | None) -> Request:
    scope = {"type": "http", "method": "GET", "path": "/x", "headers": []}
    request = Request(scope)
    request.state.auth_payload = {"iat": iat_ts} if iat_ts is not None else {}
    return request


@pytest.mark.asyncio
async def test_get_org_context_blocks_owner_when_mfa_required(monkeypatch):
    from app.api import deps as deps_module

    org_id = uuid4()
    user = SimpleNamespace(id=uuid4(), mfa_enabled=False)

    class _FakeOrgRepo:
        def __init__(self, _db):
            pass

        async def membership(self, _user_id, _org_id):
            return SimpleNamespace(role="OWNER")

        async def get_settings(self, _org_id):
            return SimpleNamespace(owner_mfa_required=True, owner_session_max_minutes=120)

    monkeypatch.setattr(deps_module, "OrgRepo", _FakeOrgRepo)

    with pytest.raises(HTTPException) as exc:
        await deps_module.get_org_context(org_id=org_id, user=user, request=_request_with_iat(int(datetime.now(tz=timezone.utc).timestamp())), db=object())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_org_context_blocks_expired_owner_session(monkeypatch):
    from app.api import deps as deps_module

    org_id = uuid4()
    user = SimpleNamespace(id=uuid4(), mfa_enabled=True)
    old_iat = int((datetime.now(tz=timezone.utc) - timedelta(minutes=45)).timestamp())

    class _FakeOrgRepo:
        def __init__(self, _db):
            pass

        async def membership(self, _user_id, _org_id):
            return SimpleNamespace(role="OWNER")

        async def get_settings(self, _org_id):
            return SimpleNamespace(owner_mfa_required=False, owner_session_max_minutes=30)

    monkeypatch.setattr(deps_module, "OrgRepo", _FakeOrgRepo)

    with pytest.raises(HTTPException) as exc:
        await deps_module.get_org_context(org_id=org_id, user=user, request=_request_with_iat(old_iat), db=object())
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_sensitive_reauth_blocks_without_reauth_token(monkeypatch):
    from app.api import deps as deps_module

    org_id = uuid4()
    user = SimpleNamespace(id=uuid4())
    old_iat = int((datetime.now(tz=timezone.utc) - timedelta(minutes=45)).timestamp())

    class _FakeOrgRepo:
        def __init__(self, _db):
            pass

        async def get_settings(self, _org_id):
            return SimpleNamespace(sensitive_action_reauth_minutes=30)

    monkeypatch.setattr(deps_module, "OrgRepo", _FakeOrgRepo)
    checker = deps_module.require_sensitive_reauth()

    with pytest.raises(HTTPException) as exc:
        await checker(
            org_id=org_id,
            request=_request_with_iat(old_iat),
            user=user,
            ctx=SimpleNamespace(role="OWNER"),
            db=object(),
        )
    assert exc.value.status_code == 401
    assert "Re-authentication is required" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_require_sensitive_reauth_accepts_valid_reauth_token(monkeypatch):
    from app.api import deps as deps_module

    org_id = uuid4()
    user = SimpleNamespace(id=uuid4())
    old_iat = int((datetime.now(tz=timezone.utc) - timedelta(minutes=45)).timestamp())
    request = _request_with_iat(old_iat)
    request.scope["headers"] = [(b"x-reauth-token", b"token-ok")]

    class _FakeOrgRepo:
        def __init__(self, _db):
            pass

        async def get_settings(self, _org_id):
            return SimpleNamespace(sensitive_action_reauth_minutes=30)

    monkeypatch.setattr(deps_module, "OrgRepo", _FakeOrgRepo)
    monkeypatch.setattr(
        deps_module,
        "decode_token",
        lambda _token: {"type": "reauth", "sub": str(user.id), "org_id": str(org_id)},
    )
    checker = deps_module.require_sensitive_reauth()

    await checker(
        org_id=org_id,
        request=request,
        user=user,
        ctx=SimpleNamespace(role="OWNER"),
        db=object(),
    )
