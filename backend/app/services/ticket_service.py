import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from app.models.tickets import Ticket, TicketCategory, TicketPriority
from app.db.session import SessionLocal
from app.models.author import Author
from app.models.book import Book
from app.models.tickets import (
    InternalNote,
    Ticket,
    TicketCategory,
    TicketEvent,
    TicketMessage,
    TicketPriority,
    TicketStatus,
)
from app.models.user import User
from app.services.ai.classification import classify_ticket
from app.services.ai.fallback_rules import classify_with_rules


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def user_role(user) -> str:
    role = user.role
    return role.value if hasattr(role, "value") else str(role)


def get_ticket_or_404(
    db: Session,
    ticket_id: uuid.UUID,
    *,
    include_messages: bool = False,
) -> Ticket:
    query = select(Ticket).where(Ticket.id == ticket_id)

    if include_messages:
        query = query.options(
            selectinload(Ticket.messages),
            selectinload(Ticket.events),
        )

    ticket = db.scalar(query)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return ticket


def ensure_ticket_access(db: Session, user, ticket: Ticket) -> None:
    if user_role(user) == "admin":
        return

    if user_role(user) != "author":
        raise HTTPException(status_code=404, detail="Ticket not found")

    author = db.scalar(
        select(Author).where(Author.user_id == user.id)
    )

    if author is None or author.id != ticket.author_id:
        raise HTTPException(status_code=404, detail="Ticket not found")


def add_event(
    db: Session,
    ticket: Ticket,
    actor_user_id: uuid.UUID,
    event_type: str,
    event_data: dict | None = None,
) -> None:
    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            event_data=event_data,
        )
    )


def generate_ticket_code(db: Session) -> str:
    # Suitable for a single-process demo. Replace with a database sequence
    # or retry-on-unique-conflict strategy for concurrent production traffic.
    latest_code = db.scalar(
        select(Ticket.ticket_code)
        .order_by(Ticket.created_at.desc())
        .limit(1)
    )

    if not latest_code or not latest_code.startswith("TKT-"):
        next_number = 1
    else:
        try:
            next_number = int(latest_code.removeprefix("TKT-")) + 1
        except ValueError:
            next_number = db.scalar(
                select(func.count()).select_from(Ticket)
            ) + 1

    return f"TKT-{next_number:04d}"


def create_ticket(
    db: Session,
    user,
    *,
    subject: str,
    description: str,
    book_id: str | None,
    category: TicketCategory,
) -> Ticket:
    if user_role(user) != "author":
        raise HTTPException(
            status_code=403,
            detail="Only authors can create tickets",
        )

    author = db.scalar(
        select(Author).where(Author.user_id == user.id)
    )

    if author is None:
        raise HTTPException(
            status_code=403,
            detail="Author profile not found",
        )

    if book_id:

        book = db.get(Book, book_id)
        if book is None or book.author_id != author.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

    now = utc_now()
    ticket = Ticket(
        ticket_code=generate_ticket_code(db),
        author_id=author.id,
        book_id=book_id,
        subject=subject,
        description=description,
        category=category,
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        classification_source="default",
        ai_status="pending",
        last_author_message_at=now,
    )

    db.add(ticket)
    db.flush()

    add_event(
        db,
        ticket,
        user.id,
        "ticket_created",
        {"status": ticket.status.value, "category": ticket.category.value},
    )
    db.commit()
    db.refresh(ticket)

    return ticket


def list_tickets(
    db: Session,
    user,
    *,
    page: int = 1,
    page_size: int = 20,
    ticket_status: TicketStatus | None = None,
    category: TicketCategory | None = None,
    priority: TicketPriority | None = None,
) -> tuple[list[Ticket], int]:
    query = select(Ticket)
    count_query = select(func.count()).select_from(Ticket)

    if user_role(user) != "admin":
      if user_role(user) != "author":
          raise HTTPException(status_code=403, detail="Access denied")

      author = db.scalar(
          select(Author).where(Author.user_id == user.id)
      )

      if author is None:
          raise HTTPException(
              status_code=403,
              detail="Author profile not found",
          )

      query = query.where(Ticket.author_id == author.id)
      count_query = count_query.where(Ticket.author_id == author.id)

      if ticket_status is not None:
          query = query.where(Ticket.status == ticket_status)
          count_query = count_query.where(Ticket.status == ticket_status)

      if category is not None:
          query = query.where(Ticket.category == category)
          count_query = count_query.where(Ticket.category == category)

    if priority is not None:
        query = query.where(Ticket.priority == priority)
        count_query = count_query.where(Ticket.priority == priority)

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(Ticket.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return list(items), total


def add_public_message(
    db: Session,
    user,
    ticket: Ticket,
    body: str,
) -> TicketMessage:
    ensure_ticket_access(db, user, ticket)

    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed tickets cannot receive replies",
        )

    role = user_role(user)
    now = utc_now()

    message = TicketMessage(
        ticket_id=ticket.id,
        sender_user_id=user.id,
        sender_role=role,
        body=body,
        used_ai_draft=False,
    )
    db.add(message)

    if role == "author":
        ticket.last_author_message_at = now

        if ticket.status == TicketStatus.RESOLVED:
            old_status = ticket.status.value
            ticket.status = TicketStatus.OPEN
            ticket.resolved_at = None
            add_event(
                db,
                ticket,
                user.id,
                "ticket_reopened",
                {"old": old_status, "new": TicketStatus.OPEN.value},
            )

    ticket.updated_at = now
    add_event(db, ticket, user.id, "message_added", {"sender_role": role})

    db.commit()
    db.refresh(message)
    return message


def update_ticket(
    db: Session,
    admin,
    ticket: Ticket,
    changes: dict,
) -> Ticket:
    if user_role(admin) != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    for field, new_value in changes.items():
        if new_value is None:
            continue

        old_value = getattr(ticket, field)

        if old_value == new_value:
            continue

        if field == "assigned_admin_id" and new_value is not None:

            assignee = db.get(User, new_value)
            if assignee is None or user_role(assignee) != "admin":
                raise HTTPException(
                    status_code=422,
                    detail="Assignee must be an existing admin",
                )

        old_serialized = (
            old_value.value if hasattr(old_value, "value") else old_value
        )
        new_serialized = (
            new_value.value if hasattr(new_value, "value") else new_value
        )

        setattr(ticket, field, new_value)

        if field == "status":
            if new_value == TicketStatus.RESOLVED:
                ticket.resolved_at = utc_now()
                ticket.closed_at = None
            elif new_value == TicketStatus.CLOSED:
                ticket.closed_at = utc_now()
            else:
                ticket.resolved_at = None
                ticket.closed_at = None

        add_event(
            db,
            ticket,
            admin.id,
            "ticket_updated",
            {
                "field": field,
                "old": old_serialized,
                "new": new_serialized,
            },
        )

    ticket.updated_at = utc_now()
    db.commit()
    db.refresh(ticket)
    return ticket


def add_internal_note(
    db: Session,
    admin,
    ticket: Ticket,
    body: str,
) -> InternalNote:
    if user_role(admin) != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    note = InternalNote(
        ticket_id=ticket.id,
        admin_user_id=admin.id,
        body=body,
    )
    db.add(note)
    add_event(db, ticket, admin.id, "internal_note_added")
    db.commit()
    db.refresh(note)
    return note


def list_internal_notes(db: Session, ticket_id: uuid.UUID) -> list[InternalNote]:
    return list(
        db.scalars(
            select(InternalNote)
            .where(InternalNote.ticket_id == ticket_id)
            .order_by(InternalNote.created_at.asc())
        ).all()
    )

logger = logging.getLogger(__name__)



def classify_ticket_background(
    ticket_id: str,
    subject: str,
    description: str,
    book_context: str = "",
) -> None:
    """Classify with AI, fall back to rules, and persist the final result."""

    logger = logging.getLogger(__name__)
    db = SessionLocal()

    try:
        ticket = db.get(Ticket, uuid.UUID(ticket_id))
        if ticket is None:
            logger.error("Classification skipped: ticket %s not found", ticket_id)
            return

        try:
            result = classify_ticket({
                "subject": subject[:500],
                "description": description[:2000],
                "book_context": book_context[:500]
                or "No book context available.",
            })

            category = TicketCategory(result.category)
            priority = TicketPriority(result.priority)

            ticket.ai_category = category.value
            ticket.ai_priority = priority.value
            ticket.ai_reason = result.reason
            ticket.classification_source = "ai"
            ticket.ai_status = "done"

        except Exception:
            logger.exception("AI classification failed for ticket %s", ticket_id)

            try:
                result = classify_with_rules(subject, description)
                category = TicketCategory(result["category"])
                priority = TicketPriority(result["priority"])

                ticket.ai_category = category.value
                ticket.ai_priority = priority.value
                ticket.ai_reason = result["reason"]
                ticket.classification_source = "rules"
                ticket.ai_status = "failed"

            except Exception:
                logger.exception("Rule-based classification failed for ticket %s", ticket_id)

                category = TicketCategory.GENERAL_INQUIRY
                priority = TicketPriority.MEDIUM

                ticket.ai_category = category.value
                ticket.ai_priority = priority.value
                ticket.ai_reason = "AI and rule-based classification both failed."
                ticket.classification_source = "rules"
                ticket.ai_status = "failed"

        ticket.category = category
        ticket.priority = priority

        db.commit()
        logger.info(
            "Classification saved: ticket=%s source=%s status=%s category=%s priority=%s",
            ticket.ticket_code,
            ticket.classification_source,
            ticket.ai_status,
            ticket.category.value,
            ticket.priority.value,
        )

    except Exception:
        db.rollback()
        logger.exception("Could not persist classification for ticket %s", ticket_id)
    finally:
        db.close()