import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.tickets.ticket import (
    TicketCategory,
    TicketPriority,
    TicketStatus,
)


class TicketCreate(BaseModel):
    subject: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=10_000)
    book_id: str | None = None
    category: TicketCategory = TicketCategory.GENERAL_INQUIRY


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    assigned_admin_id: uuid.UUID | None = None


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)


class InternalNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_user_id: uuid.UUID
    sender_role: str
    body: str
    used_ai_draft: bool
    created_at: datetime


class InternalNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admin_user_id: uuid.UUID
    body: str
    created_at: datetime


class TicketEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID
    event_type: str
    event_data: dict | None
    created_at: datetime


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_code: str
    author_id: str
    book_id: str | None
    subject: str
    description: str
    status: TicketStatus
    category: TicketCategory
    priority: TicketPriority
    classification_source: str
    ai_status: str
    ai_category: str | None
    ai_priority: str | None
    ai_reason: str | None
    assigned_admin_id: uuid.UUID | None
    last_author_message_at: datetime | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None


class TicketDetailResponse(TicketResponse):
    messages: list[MessageResponse]
    events: list[TicketEventResponse]


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    total: int
    page: int
    page_size: int


class InternalNoteListResponse(BaseModel):
    items: list[InternalNoteResponse]