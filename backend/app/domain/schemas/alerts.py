import uuid
from datetime import datetime

from pydantic import BaseModel

from app.domain.schemas.common import ORMModel


class AlertOut(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID
    location_id: uuid.UUID | None = None
    kind: str
    severity: str
    title: str
    description: str
    meta: dict
    status: str
    assigned_to_user_id: uuid.UUID | None = None
    assigned_by_user_id: uuid.UUID | None = None
    assigned_at: datetime | None = None
    acknowledged_at: datetime | None = None
    created_at: datetime


class AlertsOut(BaseModel):
    items: list[AlertOut]


class AlertAssignIn(BaseModel):
    org_id: uuid.UUID
    assignee_user_id: uuid.UUID | None = None


class AlertAcknowledgeIn(BaseModel):
    org_id: uuid.UUID


class AlertHistoryItem(BaseModel):
    id: uuid.UUID
    action: str
    actor_user_id: uuid.UUID | None
    metadata_json: dict
    created_at: datetime


class AlertHistoryOut(BaseModel):
    items: list[AlertHistoryItem]
