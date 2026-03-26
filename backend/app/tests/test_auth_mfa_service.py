from datetime import timedelta
from types import SimpleNamespace
import uuid

import pytest

from app.core.mfa import _totp_code, encrypt_mfa_secret
from app.domain.services.auth_service import AuthService, UnauthorizedError


class _FakeAuthRepo:
    def __init__(self, user):
        self.user = user
        self.created_sessions = 0
        self.saved = 0

    async def get_user_by_email(self, email: str):
        return self.user if self.user.email == email else None

    async def create_token_session(self, **_kwargs):
        self.created_sessions += 1
        return SimpleNamespace(id=uuid.uuid4())

    async def save_user(self, user):
        self.user = user
        self.saved += 1
        return user


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
async def test_login_requires_mfa_code_when_enabled(monkeypatch):
    user_id = uuid.uuid4()
    from app.core.security import hash_password

    secret = "JBSWY3DPEHPK3PXP"
    user = SimpleNamespace(
        id=user_id,
        email="owner@example.com",
        is_active=True,
        password_hash=hash_password("Password123!"),
        mfa_enabled=True,
        mfa_secret_encrypted=encrypt_mfa_secret(secret),
        mfa_recovery_code_hashes=[],
    )
    svc = AuthService(_FakeAuthRepo(user), _FakeOrgRepo(), _FakeAuditRepo(), None)  # type: ignore[arg-type]

    with pytest.raises(UnauthorizedError, match="MFA code required"):
        await svc.login("owner@example.com", "Password123!", _Req(), None)


@pytest.mark.asyncio
async def test_login_succeeds_with_valid_mfa_code(monkeypatch):
    user_id = uuid.uuid4()
    from app.core.security import hash_password

    secret = "JBSWY3DPEHPK3PXP"
    user = SimpleNamespace(
        id=user_id,
        email="owner@example.com",
        is_active=True,
        password_hash=hash_password("Password123!"),
        mfa_enabled=True,
        mfa_secret_encrypted=encrypt_mfa_secret(secret),
        mfa_recovery_code_hashes=[],
    )
    repo = _FakeAuthRepo(user)
    svc = AuthService(repo, _FakeOrgRepo(), _FakeAuditRepo(), None)  # type: ignore[arg-type]

    fixed_now = 1711281600  # 2024-03-24T12:00:00Z

    class _FakeDateTime:
        @staticmethod
        def now(_tz=None):
            from datetime import datetime, timezone

            return datetime.fromtimestamp(fixed_now, tz=timezone.utc)

    monkeypatch.setattr("app.core.mfa.datetime", _FakeDateTime)
    code = _totp_code(secret, fixed_now // 30)
    out = await svc.login("owner@example.com", "Password123!", _Req(), code)

    assert out.access_token
    assert out.refresh_token
    assert repo.created_sessions == 1


@pytest.mark.asyncio
async def test_login_succeeds_with_valid_recovery_code_and_consumes_it():
    user_id = uuid.uuid4()
    from app.core.security import hash_password
    from app.domain.services.auth_service import _h

    recovery = "AB12CD34"
    secret = "JBSWY3DPEHPK3PXP"
    user = SimpleNamespace(
        id=user_id,
        email="owner@example.com",
        is_active=True,
        password_hash=hash_password("Password123!"),
        mfa_enabled=True,
        mfa_secret_encrypted=encrypt_mfa_secret(secret),
        mfa_recovery_code_hashes=[_h(recovery)],
    )
    repo = _FakeAuthRepo(user)
    svc = AuthService(repo, _FakeOrgRepo(), _FakeAuditRepo(), None)  # type: ignore[arg-type]

    out = await svc.login("owner@example.com", "Password123!", _Req(), None, recovery)

    assert out.access_token
    assert out.refresh_token
    assert repo.created_sessions == 1
    assert repo.saved == 1
    assert repo.user.mfa_recovery_code_hashes == []
