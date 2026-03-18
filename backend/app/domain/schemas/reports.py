import uuid
from datetime import date, datetime

from pydantic import BaseModel


class ReportItem(BaseModel):
    id: uuid.UUID
    week_start: date
    week_end: date
    created_at: datetime


class ReportsOut(BaseModel):
    items: list[ReportItem]


class ReportGenerateOut(BaseModel):
    report_id: uuid.UUID | None = None
    job_id: str
    status: str
