import uuid
from datetime import datetime

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: uuid.UUID
    kind: str
    severity: str
    title: str
    description: str
    meta: dict
    status: str
    created_at: datetime


class AlertsOut(BaseModel):
    items: list[AlertOut]
