import uuid
from datetime import date

from pydantic import BaseModel, Field


class AISummaryRequest(BaseModel):
    org_id: uuid.UUID
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")


class AISummaryResponse(BaseModel):
    headline: str
    highlights: list[str]
    risks: list[str]
    actions: list[str]
    confidence: str


class AISummaryOut(BaseModel):
    summary_json: AISummaryResponse
    fallback_used: bool
