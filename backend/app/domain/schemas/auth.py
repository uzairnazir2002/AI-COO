import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(RegisterIn):
    mfa_code: str | None = Field(default=None, min_length=6, max_length=6)
    mfa_recovery_code: str | None = Field(default=None, min_length=8, max_length=64)


class TokenRefreshIn(BaseModel):
    refresh_token: str | None = None


class LogoutIn(BaseModel):
    refresh_token: str | None = None


class RegisterOut(BaseModel):
    user_id: uuid.UUID
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    account_confirmed: bool = False


class InviteAcceptIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class ConfirmIn(BaseModel):
    token: str
    password: str | None = Field(default=None, min_length=8, max_length=128)


class ResendConfirmationIn(BaseModel):
    email: EmailStr


class ResendConfirmationOut(BaseModel):
    ok: bool
    sent: bool
    already_active: bool = False


class DevConfirmationTokenOut(BaseModel):
    email: EmailStr
    token: str | None = None
    found: bool


class TokenOut(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class MeOrg(BaseModel):
    org_id: uuid.UUID
    role: str
    name: str


class MeUser(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime


class MeOut(BaseModel):
    user: MeUser
    orgs: list[MeOrg]


class MfaSetupIn(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class MfaSetupOut(BaseModel):
    secret: str
    otpauth_url: str


class MfaEnableIn(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class MfaDisableIn(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    code: str = Field(min_length=6, max_length=6)


class MfaStatusOut(BaseModel):
    enabled: bool
    configured: bool
    enabled_at: datetime | None
    recovery_codes_remaining: int = 0


class MfaRecoveryCodesOut(BaseModel):
    recovery_codes: list[str]


class MfaRecoveryCodesRegenerateIn(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    code: str = Field(min_length=6, max_length=6)


class SessionOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    user_agent: str | None
    ip_address: str | None
    is_revoked: bool
    is_current: bool


class SessionListOut(BaseModel):
    items: list[SessionOut]


class RevokeOthersIn(BaseModel):
    refresh_token: str | None = None


class ReauthIn(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=6)
    mfa_recovery_code: str | None = Field(default=None, min_length=8, max_length=64)


class ReauthOut(BaseModel):
    ok: bool
    token: str
    token_type: str = "reauth"
    expires_in: int


class AccountDeletionRequestIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class DeletionRequestOut(BaseModel):
    ok: bool
    request_id: uuid.UUID
    delete_after: datetime
