import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(RegisterIn):
    pass


class TokenRefreshIn(BaseModel):
    refresh_token: str | None = None


class LogoutIn(BaseModel):
    refresh_token: str | None = None


class RegisterOut(BaseModel):
    user_id: uuid.UUID


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
