import uuid
from datetime import datetime

from pydantic import BaseModel

from app.domain.schemas.common import ORMModel


class NotificationOut(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID | None
    user_id: uuid.UUID | None
    category: str
    title: str
    message: str | None
    link: str | None
    is_read: bool
    metadata_json: dict
    created_at: datetime


class NotificationPageOut(BaseModel):
    items: list[NotificationOut]
    page: int
    page_size: int
    total: int
    unread_count: int
