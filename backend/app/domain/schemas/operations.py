import uuid
from datetime import datetime

from pydantic import BaseModel

from app.domain.schemas.common import ORMModel
from app.domain.schemas.job import JobOut


class OutboxEventOut(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID | None
    event_type: str
    payload: dict
    status: str
    attempts: int
    max_attempts: int
    available_at: datetime
    sent_at: datetime | None
    last_error: str | None
    correlation_id: str | None
    dedupe_key: str | None
    created_at: datetime
    updated_at: datetime | None = None


class OutboxPageOut(BaseModel):
    items: list[OutboxEventOut]
    page: int
    page_size: int
    total: int
    counts_by_status: dict[str, int]


class BeatScheduleItemOut(BaseModel):
    name: str
    task: str
    schedule: str
    paused: bool


class SystemStatusOut(BaseModel):
    scheduler: list[BeatScheduleItemOut]
    system_jobs: list[JobOut]
    system_job_total: int
    org_outbox_counts: dict[str, int]


class RuntimeMetricsOut(BaseModel):
    org_id: uuid.UUID
    queue_depth_active: int
    outbox_pending: int
    db_active_connections: int
