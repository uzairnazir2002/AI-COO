from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.security import hash_password
from app.domain.services.auth_service import AuthService
from app.domain.services.errors import UnauthorizedError


class _FakeAuthRepo:
    def __init__(self, user):
        self.user = user

    async def get_user_by_email(self, _email):
        return self.user

    async def save_user(self, _user):
        return None

    async def create_token_session(self, **_kwargs):
        return None


class _FakeOrgRepo:
    async def owner_org_ids_requiring_mfa(self, _user_id):
        return [uuid4()]


class _FakeAuditRepo:
    async def log(self, *_args, **_kwargs):
        return None


@pytest.mark.asyncio
async def test_login_blocks_owner_without_mfa_when_policy_requires_it():
    user = SimpleNamespace(
        id=uuid4(),
        email="owner@example.com",
        is_active=True,
        password_hash=hash_password("Password123!"),
        mfa_enabled=False,
        mfa_secret_encrypted=None,
        mfa_recovery_code_hashes=[],
        created_at=datetime.now(tz=timezone.utc),
    )
    svc = AuthService(_FakeAuthRepo(user), _FakeOrgRepo(), _FakeAuditRepo())
    request = SimpleNamespace(headers={}, client=None)

    with pytest.raises(UnauthorizedError, match="organization policy"):
        await svc.login("owner@example.com", "Password123!", request)
