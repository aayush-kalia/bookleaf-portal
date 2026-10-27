import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCategory(str, enum.Enum):
    ROYALTY_PAYMENTS = "royalty_payments"
    ISBN_METADATA = "isbn_metadata"
    PRINTING_QUALITY = "printing_quality"
    DISTRIBUTION_AVAILABILITY = "distribution_availability"
    PRODUCTION_STATUS = "production_status"
    GENERAL_INQUIRY = "general_inquiry"


class TicketPriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def enum_values(enum_class):
    return [item.value for item in enum_class]


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticket_code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )

    # Author IDs are strings in the supplied BookLeaf seed data.
    author_id: Mapped[str] = mapped_column(
    String(20),
    ForeignKey("authors.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
)

    book_id: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("books.id", ondelete="SET NULL"),
        nullable=True,
    )

    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[TicketStatus] = mapped_column(
        Enum(
            TicketStatus,
            name="ticket_status",
            values_callable=enum_values,
        ),
        default=TicketStatus.OPEN,
        nullable=False,
        index=True,
    )
    category: Mapped[TicketCategory] = mapped_column(
        Enum(
            TicketCategory,
            name="ticket_category",
            values_callable=enum_values,
        ),
        default=TicketCategory.GENERAL_INQUIRY,
        nullable=False,
        index=True,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(
            TicketPriority,
            name="ticket_priority",
            values_callable=enum_values,
        ),
        default=TicketPriority.MEDIUM,
        nullable=False,
        index=True,
    )

    classification_source: Mapped[str] = mapped_column(
        String(20), default="default", nullable=False
    )
    ai_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )

    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)

    last_author_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    messages = relationship(
        "TicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketMessage.created_at",
    )
    internal_notes = relationship(
        "InternalNote",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="InternalNote.created_at",
    )
    events = relationship(
        "TicketEvent",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketEvent.created_at",
    )