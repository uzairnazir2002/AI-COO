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

    async def create_confirmation_token(self, user_id: uuid.UUID, token_hash: str, expires_at):
        token = _TokenRec(user_id=user_id, token_hash=token_hash)
        token.expires_at = expires_at
        self.tokens_by_hash[token_hash] = token
        return token

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
    assert "Confirm your AI COO account" in event["payload"]["subject"]
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

    out = await svc.confirm_registration(raw)

    assert out.id == user.id
    assert out.is_active is True
    assert token.used_at is not None
    assert "auth.confirm" in audit_repo.actions


@pytest.mark.asyncio
async def test_confirm_registration_rejects_invalid_token():
    auth_repo = _FakeAuthRepo()
    svc = AuthService(auth_repo, _FakeOrgRepo(), _FakeAuditRepo(), _FakeOutboxRepo())  # type: ignore[arg-type]

    with pytest.raises(UnauthorizedError):
        await svc.confirm_registration("invalid-token")


@pytest.mark.asyncio
async def test_resend_confirmation_creates_new_outbox_event_for_inactive_user():
    auth_repo = _FakeAuthRepo()
    outbox_repo = _FakeOutboxRepo()
    audit_repo = _FakeAuditRepo()
    svc = AuthService(auth_repo, _FakeOrgRepo(), audit_repo, outbox_repo)  # type: ignore[arg-type]
    await auth_repo.create_user("owner@example.com", "hash", is_active=False)

    sent, already_active = await svc.resend_confirmation("owner@example.com")

    assert sent is True
    assert already_active is False
    assert len(outbox_repo.events) == 1
    assert outbox_repo.events[0]["payload"]["to"] == "owner@example.com"
    assert "auth.confirm.resend" in audit_repo.actions
