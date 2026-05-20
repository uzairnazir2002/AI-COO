import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class AnnouncementAttachmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2000)


class WorkforceAnnouncementCreateIn(BaseModel):
    org_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1)
    priority: str = Field(default="NORMAL", max_length=16)
    pinned: bool = False
    acknowledgement_required: bool = False
    expires_at: date | None = None
    scheduled_publish_at: datetime | None = None
    audience_kind: str = Field(default="ORG_ALL", max_length=24)
    audience_ids: list[uuid.UUID] | None = None
    attachments: list[AnnouncementAttachmentIn] | None = None
    send_email_on_publish: bool = False
    template_id: uuid.UUID | None = None


class WorkforceAnnouncementUpdateIn(BaseModel):
    org_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    body: str | None = Field(default=None, min_length=1)
    priority: str | None = Field(default=None, max_length=16)
    pinned: bool | None = None
    acknowledgement_required: bool | None = None
    expires_at: date | None = None
    scheduled_publish_at: datetime | None = None
    audience_kind: str | None = Field(default=None, max_length=24)
    audience_ids: list[uuid.UUID] | None = None
    audience_ids_clear: bool = False
    attachments: list[AnnouncementAttachmentIn] | None = None
    attachments_clear: bool = False
    send_email_on_publish: bool | None = None
    template_id: uuid.UUID | None = None
    template_clear: bool = False


class WorkforceAnnouncementPublishIn(BaseModel):
    org_id: uuid.UUID | None = None


class WorkforceAnnouncementArchiveIn(BaseModel):
    org_id: uuid.UUID | None = None


class WorkforceAnnouncementAcknowledgeIn(BaseModel):
    org_id: uuid.UUID | None = None


class WorkforceAnnouncementReceiptOut(BaseModel):
    read_at: datetime | None = None
    acknowledged_at: datetime | None = None

    model_config = {"from_attributes": True}


class WorkforceAnnouncementOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    template_id: uuid.UUID | None = None
    title: str
    body: str
    priority: str
    status: str
    published_at: datetime | None = None
    scheduled_publish_at: datetime | None = None
    expires_at: date | None = None
    pinned: bool
    acknowledgement_required: bool
    audience_kind: str
    audience_ids: list[str] | None = None
    attachments_json: list[dict[str, Any]] | None = None
    send_email_on_publish: bool
    automation_dedupe_key: str | None = None
    created_at: datetime
    updated_at: datetime
    my_receipt: WorkforceAnnouncementReceiptOut | None = None

    model_config = {"from_attributes": True}


class WorkforceAnnouncementDetailOut(WorkforceAnnouncementOut):
    pass


class WorkforceAnnouncementDeliveryOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    announcement_id: uuid.UUID
    channel: str
    user_id: uuid.UUID | None = None
    recipient_email: str
    status: str
    error: str | None = None
    outbox_event_id: uuid.UUID | None = None
    sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    outbox_status: str | None = None
    outbox_attempts: int | None = None
    outbox_last_error: str | None = None

    model_config = {"from_attributes": True}


class WorkforceAnnouncementDeliveryListOut(BaseModel):
    items: list[WorkforceAnnouncementDeliveryOut]
    total: int
    page: int
    page_size: int


class WorkforceAnnouncementAttachmentUploadOut(BaseModel):
    name: str
    url: str
    content_type: str
    size_bytes: int


class WorkforceAutomationKeysOut(BaseModel):
    keys: list[str]


class WorkforceAnnouncementTemplateCreateIn(BaseModel):
    org_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    body_template: str = Field(min_length=1)
    code: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=500)
    automation_key: str | None = Field(default=None, max_length=64)


class WorkforceAnnouncementTemplateUpdateIn(BaseModel):
    org_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    body_template: str | None = Field(default=None, min_length=1)
    code: str | None = Field(default=None, max_length=64)
    code_clear: bool = False
    description: str | None = Field(default=None, max_length=500)
    description_clear: bool = False
    automation_key: str | None = Field(default=None, max_length=64)
    automation_clear: bool = False
    is_active: bool | None = None


class WorkforceAnnouncementTemplateOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    name: str
    code: str | None = None
    description: str | None = None
    body_template: str
    automation_key: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
