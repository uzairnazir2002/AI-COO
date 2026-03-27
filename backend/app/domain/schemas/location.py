import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LocationCreateIn(BaseModel):
    org_id: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    is_active: bool = True


class LocationUpdateIn(BaseModel):
    org_id: uuid.UUID
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    is_active: bool | None = None


class LocationOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    name: str
    code: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
