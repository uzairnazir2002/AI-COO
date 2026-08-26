import uuid
from datetime import timedelta

import pytest

from app.domain.services.auth_service import AuthService, UnauthorizedError, _h
from app.utils.time import utc_now


class _User:
    def __init__(self, email: str, is_active: bool):
        self.id = uuid.uuid4()
        self.email = email
        self.password_hash = "hash"
        self.is_active = is_active


class _TokenRec:
    def __init__(self, user_id: uuid.UUID, token_hash: str):
        self.id = uuid.uuid4()
        self.user_id = user_id
        self.token_hash = token_hash
        self.expires_at = utc_now() + timedelta(hours=24)
        self.used_at = None
        self.invalidated_at = None
        self.code_hash = None
        self.code_expires_at = None
        self.code_attempts = 0
        self.code_max_attempts = 5


class _FakeAuthRepo:
    def __init__(self):
        self.user_by_email = {}
        self.user_by_id = {}
        self.tokens_by_hash = {}

    async def get_user_by_email(self, email: str):
        return self.user_by_email.get(email)

    async def create_user(self, email: str, password_hash: str, is_active: bool):
        user = _User(email=email, is_active=is_active)
        user.password_hash = password_hash
        self.user_by_email[email] = user
        self.user_by_id[user.id] = user
        return user

    async def create_confirmation_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at,
        *,
        code_hash: str | None = None,
        code_expires_at=None,
        code_max_attempts: int = 5,
    ):
        token = _TokenRec(user_id=user_id, token_hash=token_hash)
        token.expires_at = expires_at
        token.code_hash = code_hash
        token.code_expires_at = code_expires_at
        token.code_max_attempts = code_max_attempts
        self.tokens_by_hash[token_hash] = token
        if code_hash:
            self.tokens_by_hash[code_hash] = token
        return token

    async def invalidate_unused_confirmation_tokens(self, _user_id: uuid.UUID):
        return 0

    async def get_confirmation_token_by_code_hash_for_user(self, *, user_id: uuid.UUID, code_hash: str):
        rec = self.tokens_by_hash.get(code_hash)
        if rec and rec.user_id == user_id:
            return rec
        return None

    async def get_pending_confirmation_token_for_user(self, user_id: uuid.UUID):
        for token in self.tokens_by_hash.values():
            if token.user_id == user_id and token.used_at is None and token.invalidated_at is None:
                return token
        return None

    async def increment_confirmation_code_attempts(self, token):
        token.code_attempts += 1

    async def get_confirmation_token(self, token_hash: str):
        return self.tokens_by_hash.get(token_hash)

    async def get_user(self, user_id: uuid.UUID):
        return self.user_by_id.get(user_id)

    async def save_user(self, user):
        self.user_by_id[user.id] = user
        self.user_by_email[user.email] = user
        return user

    async def mark_confirmation_token_used(self, token):
        token.used_at = utc_now()


class _FakeOutboxRepo:
    def __init__(self):
        self.events = []

    async def create_event(self, **kwargs):
        self.events.append(kwargs)
        return kwargs


class _FakeOrgRepo:
    pass


class _FakeAuditRepo:
    def __init__(self):
        self.actions = []

    async def log(self, _actor_user_id, _org_id, action, _entity_type, _entity_id, _metadata):
        self.actions.append(action)


@pytest.mark.asyncio
async def test_register_creates_inactive_user_and_confirmation_outbox_event():
    auth_repo = _FakeAuthRepo()
    outbox_repo = _FakeOutboxRepo()
    audit_repo = _FakeAuditRepo()
    svc = AuthService(auth_repo, _FakeOrgRepo(), audit_repo, outbox_repo)  # type: ignore[arg-type]

    user = await svc.register("owner@example.com", "Password123!")

    assert user.is_active is False
    assert len(outbox_repo.events) == 1
    event = outbox_repo.events[0]
    assert event["event_type"] == "email.send"
    assert event["payload"]["to"] == "owner@example.com"
    assert "Confirm your AI-COO account" in event["payload"]["subject"]
    assert "/auth/confirm?token=" in event["payload"]["body"]
    assert "6-digit confirmation code" in event["payload"]["body"]
    assert "auth.register" in audit_repo.actions


@pytest.mark.asyncio
async def test_confirm_registration_activates_user_and_marks_token_used():
    auth_repo = _FakeAuthRepo()
    outbox_repo = _FakeOutboxRepo()
    audit_repo = _FakeAuditRepo()
    svc = AuthService(auth_repo, _FakeOrgRepo(), audit_repo, outbox_repo)  # type: ignore[arg-type]

    user = await auth_repo.create_user("owner@example.com", "hash", is_active=False)
    raw = "confirm-token"
    token = await auth_repo.create_confirmation_token(user.id, _h(raw), utc_now() + timedelta(hours=24))

    out = await svc.confirm_registration(token=raw)

    assert out.id == user.id
    assert out.is_active is True
    assert token.used_at is not None
    assert "auth.confirm" in audit_repo.actions


@pytest.mark.asyncio
async def test_confirm_registration_rejects_invalid_token():
    auth_repo = _FakeAuthRepo()
    svc = AuthService(auth_repo, _FakeOrgRepo(), _FakeAuditRepo(), _FakeOutboxRepo())  # type: ignore[arg-type]

    with pytest.raises(UnauthorizedError):
        await svc.confirm_registration(token="invalid-token")


@pytest.mark.asyncio
async def test_resend_confirmation_creates_new_outbox_event_for_inactive_user():
    auth_repo = _FakeAuthRepo()
    outbox_repo = _FakeOutboxRepo()
    audit_repo = _FakeAuditRepo()
    svc = AuthService(auth_repo, _FakeOrgRepo(), audit_repo, outbox_repo)  # type: ignore[arg-type]
    await auth_repo.create_user("owner@example.com", "hash", is_active=False)

    await svc.resend_confirmation("owner@example.com")
    assert len(outbox_repo.events) == 1
    assert outbox_repo.events[0]["payload"]["to"] == "owner@example.com"
    assert "auth.confirm.resend" in audit_repo.actions
