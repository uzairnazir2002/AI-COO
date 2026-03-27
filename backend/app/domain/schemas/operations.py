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
    queue_lag_seconds: int
    queue_lag_breach: bool
    outbox_pending: int
    dead_letter_open: int
    worker_health: str
    db_active_connections: int
    auth_lockout_failures_total: int = 0
    auth_lockouts_total: int = 0
    auth_lockout_escalations_total: int = 0


class EndpointSLOOut(BaseModel):
    endpoint: str
    requests: int
    p95_ms: float
    error_rate_pct: float
    breach: bool


class RuntimeSLOOut(BaseModel):
    org_id: uuid.UUID
    window_seconds: int
    p95_threshold_ms: float
    error_rate_threshold_pct: float
    total_requests: int
    endpoints: list[EndpointSLOOut]


class DeadLetterEventOut(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID | None
    source_type: str
    source_id: uuid.UUID | None
    source_task_id: str | None
    source_name: str
    status: str
    attempts: int
    last_error: str | None
    payload: dict
    metadata_json: dict
    first_failed_at: datetime
    last_failed_at: datetime
    replayed_at: datetime | None
    created_at: datetime
    updated_at: datetime | None = None


class DeadLetterPageOut(BaseModel):
    items: list[DeadLetterEventOut]
    page: int
    page_size: int
    total: int
    counts_by_status: dict[str, int]
