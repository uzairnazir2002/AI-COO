import uuid
from datetime import datetime

from pydantic import BaseModel
from app.domain.schemas.common import ORMModel


class DeletionRequestItemOut(ORMModel):
    id: uuid.UUID
    scope: str
    status: str
    requested_by_user_id: uuid.UUID | None
    target_user_id: uuid.UUID | None
    target_org_id: uuid.UUID | None
    reason: str | None
    delete_after: datetime
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DeletionRequestListOut(BaseModel):
    items: list[DeletionRequestItemOut]
