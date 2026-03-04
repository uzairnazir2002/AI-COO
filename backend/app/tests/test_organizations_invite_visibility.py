import os
import uuid
from types import SimpleNamespace

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.api.v1 import organizations as organizations_api
from app.domain.schemas.organization import InviteIn


class _FakeDB:
    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_invite_hides_token_when_exposure_disabled(monkeypatch):
    class _FakeOrgService:
        def __init__(self, *args, **kwargs):
            pass

        async def invite(self, actor_user_id, org_id, email, role):
            return "tok-hidden"

    monkeypatch.setattr(organizations_api, "OrgService", _FakeOrgService)
    monkeypatch.setattr(
        organizations_api,
        "get_app_settings",
        lambda: SimpleNamespace(expose_invite_token_in_response=False),
    )

    db = _FakeDB()
    user = SimpleNamespace(id=uuid.uuid4())
    out = await organizations_api.invite(
        org_id=uuid.uuid4(),
        body=InviteIn(email="owner@example.com", role="EDITOR"),
        user=user,
        _=object(),
        db=db,
    )

    assert db.committed is True
    assert out == {"ok": True}


@pytest.mark.asyncio
async def test_invite_returns_token_when_exposure_enabled(monkeypatch):
    class _FakeOrgService:
        def __init__(self, *args, **kwargs):
            pass

        async def invite(self, actor_user_id, org_id, email, role):
            return "tok-visible"

    monkeypatch.setattr(organizations_api, "OrgService", _FakeOrgService)
    monkeypatch.setattr(
        organizations_api,
        "get_app_settings",
        lambda: SimpleNamespace(expose_invite_token_in_response=True),
    )

    db = _FakeDB()
    user = SimpleNamespace(id=uuid.uuid4())
    out = await organizations_api.invite(
        org_id=uuid.uuid4(),
        body=InviteIn(email="owner@example.com", role="VIEWER"),
        user=user,
        _=object(),
        db=db,
    )

    assert db.committed is True
    assert out == {"ok": True, "invite_token": "tok-visible"}
