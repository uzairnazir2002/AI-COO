import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class WorkforcePolicyCreateIn(BaseModel):
    org_id: uuid.UUID
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1)
    requires_ack: bool = True
    publish_now: bool = False
    is_active: bool = True


class WorkforcePolicyOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    code: str
    title: str
    body: str
    version: int
    requires_ack: bool
    is_active: bool
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkforcePolicyPublishIn(BaseModel):
    org_id: uuid.UUID


class WorkforcePolicyAckCreateIn(BaseModel):
    org_id: uuid.UUID
    employee_id: uuid.UUID


class WorkforcePolicyAckOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    policy_id: uuid.UUID
    employee_id: uuid.UUID
    acknowledged_at: datetime
    acknowledged_by_user_id: uuid.UUID

    model_config = {"from_attributes": True}


class WorkforceDocumentOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    employee_id: uuid.UUID | None
    policy_id: uuid.UUID | None
    name: str
    content_type: str
    size_bytes: int
    object_key: str
    url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkforceDocumentDeactivateIn(BaseModel):
    org_id: uuid.UUID


class WorkforceDocumentUploadOut(BaseModel):
    name: str
    url: str
    content_type: str
    size_bytes: int
    object_key: str


class WorkforceChecklistItemCreateIn(BaseModel):
    org_id: uuid.UUID
    employee_id: uuid.UUID
    kind: str = Field(max_length=16)  # ONBOARDING | OFFBOARDING
    title: str = Field(min_length=1, max_length=240)
    details: str | None = Field(default=None, max_length=1000)
    due_date: date | None = None


class WorkforceChecklistItemOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    employee_id: uuid.UUID
    kind: str
    title: str
    details: str | None
    due_date: date | None
    is_done: bool
    completed_at: datetime | None
    completed_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkforceChecklistDoneIn(BaseModel):
    org_id: uuid.UUID
    is_done: bool

