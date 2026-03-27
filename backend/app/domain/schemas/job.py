import uuid
from datetime import datetime

from pydantic import BaseModel

from app.domain.schemas.common import ORMModel


class JobOut(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID | None
    task_id: str
    task_name: str
    dedupe_key: str
    status: str
    progress: int
    payload: dict
    result: dict | None
    request_id: str | None
    correlation_id: str | None
    last_error: str | None
    traceback_summary: str | None
    retry_count: int
    last_retry_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobCommandResult(BaseModel):
    ok: bool
    job_id: str
    status: str
    new_task_id: str | None = None


class JobPageOut(BaseModel):
    items: list[JobOut]
    page: int
    page_size: int
    total: int
