import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from app.services.ticket_service import classify_ticket_background
from app.db.dependencies import get_db
from app.api.dependencies import get_current_user
from app.models.tickets import Ticket, TicketCategory, TicketPriority, TicketStatus
from app.schemas.ticket import (
    InternalNoteCreate,
    InternalNoteListResponse,
    InternalNoteResponse,
    MessageCreate,
    MessageResponse,
    TicketCreate,
    TicketDetailResponse,
    TicketEventResponse,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)
from app.services import ticket_service as service

router = APIRouter(prefix="/tickets", tags=["Tickets"])


def require_admin(user) -> None:
    if service.user_role(user) != "admin":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admin access required")


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    payload: TicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ticket = service.create_ticket(
        db,
        current_user,
        subject=payload.subject,
        description=payload.description,
        book_id=payload.book_id,
        category=payload.category,
    )

    background_tasks.add_task(
        classify_ticket_background,
        str(ticket.id),
        ticket.subject,
        ticket.description,
        "",
    )

    return ticket


@router.get("", response_model=TicketListResponse)
def get_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ticket_status: TicketStatus | None = Query(None, alias="status"),
    category: TicketCategory | None = None,
    priority: TicketPriority | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    items, total = service.list_tickets(
        db,
        current_user,
        page=page,
        page_size=page_size,
        ticket_status=ticket_status,
        category=category,
        priority=priority,
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ticket = service.get_ticket_or_404(
        db, ticket_id, include_messages=True
    )
    service.ensure_ticket_access(db, current_user, ticket)
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def patch_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_admin(current_user)
    ticket = service.get_ticket_or_404(db, ticket_id)

    changes = payload.model_dump(exclude_unset=True)
    return service.update_ticket(db, current_user, ticket, changes)


@router.post(
    "/{ticket_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_message(
    ticket_id: uuid.UUID,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ticket = service.get_ticket_or_404(db, ticket_id)
    return service.add_public_message(
        db, current_user, ticket, payload.body
    )


@router.get(
    "/{ticket_id}/notes",
    response_model=InternalNoteListResponse,
)
def get_internal_notes(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_admin(current_user)
    service.get_ticket_or_404(db, ticket_id)

    return {
        "items": service.list_internal_notes(db, ticket_id)
    }


@router.post(
    "/{ticket_id}/notes",
    response_model=InternalNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_internal_note(
    ticket_id: uuid.UUID,
    payload: InternalNoteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_admin(current_user)
    ticket = service.get_ticket_or_404(db, ticket_id)

    return service.add_internal_note(
        db, current_user, ticket, payload.body
    )