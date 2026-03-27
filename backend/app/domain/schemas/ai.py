import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domain.schemas.common import ORMModel


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


class AIChatSessionCreateIn(BaseModel):
    org_id: uuid.UUID
    title: str | None = Field(default=None, max_length=200)


class AIChatSessionOut(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    title: str
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


class AIChatMessageOut(ORMModel):
    id: uuid.UUID
    session_id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    role: str
    content: str
    fallback_used: bool
    grounding_violations: list[str]
    created_at: datetime


class AIChatSessionDetailOut(BaseModel):
    session: AIChatSessionOut
    messages: list[AIChatMessageOut]


class AIChatRequest(BaseModel):
    org_id: uuid.UUID
    session_id: uuid.UUID
    message: str = Field(min_length=1, max_length=4000)
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")


class AIChatOut(BaseModel):
    session_id: uuid.UUID
    message: AIChatMessageOut


class AIProviderHealthOut(BaseModel):
    provider: str
    model: str | None = None
    configured: bool
    healthy: bool
    live_check_performed: bool
    reason: str | None = None


class AIHealthOut(BaseModel):
    provider: AIProviderHealthOut
    fallback_ready: bool
