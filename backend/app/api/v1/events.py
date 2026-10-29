import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select

from app.api.dependencies import get_current_user
from app.db.session import SessionLocal
from app.models.author import Author
from app.models.tickets import Ticket, TicketEvent
from app.services.ticket_service import user_role

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/stream")
async def stream_events(
    last_event_id: UUID | None = Query(None),
    last_event_header: str | None = Header(None, alias="Last-Event-ID"),
    current_user=Depends(get_current_user),
):
    role = user_role(current_user)

    if role not in {"admin", "author"}:
        raise HTTPException(status_code=403, detail="Access denied")

    # Native EventSource sends Last-Event-ID when reconnecting.
    cursor = last_event_id
    if last_event_header:
        try:
            cursor = UUID(last_event_header)
        except ValueError:
            cursor = None

    author_id = None

    if role == "author":
        with SessionLocal() as db:
            author = db.scalar(
                select(Author).where(Author.user_id == current_user.id)
            )
            if author is None:
                raise HTTPException(
                    status_code=403,
                    detail="Author profile not found",
                )
            author_id = author.id

    def visible_events_query():
        query = (
            select(TicketEvent)
            .join(Ticket, Ticket.id == TicketEvent.ticket_id)
        )

        if role == "author":
            query = query.where(
                Ticket.author_id == author_id,
                TicketEvent.event_type != "internal_note_added",
            )

        return query

    def get_baseline():
        # Only use a cursor that exists and is visible to this user.
        with SessionLocal() as db:
            if cursor is not None:
                visible_cursor = db.scalar(
                    visible_events_query().where(TicketEvent.id == cursor)
                )
                if visible_cursor is not None:
                    return cursor

            latest = db.scalar(
                visible_events_query()
                .order_by(
                    TicketEvent.created_at.desc(),
                    TicketEvent.id.desc(),
                )
                .limit(1)
            )
            return latest.id if latest is not None else None

    async def event_generator():
        current_cursor = get_baseline()
        yield "retry: 3000\n\n"

        while True:
            with SessionLocal() as db:
                query = visible_events_query()

                if current_cursor is not None:
                    cursor_event = db.get(TicketEvent, current_cursor)

                    if cursor_event is not None:
                        query = query.where(
                            or_(
                                TicketEvent.created_at
                                > cursor_event.created_at,
                                (
                                    TicketEvent.created_at
                                    == cursor_event.created_at
                                )
                                & (TicketEvent.id > cursor_event.id),
                            )
                        )

                events = db.scalars(
                    query.order_by(
                        TicketEvent.created_at,
                        TicketEvent.id,
                    ).limit(100)
                ).all()

                payloads = [
                    {
                        "id": str(event.id),
                        "ticket_id": str(event.ticket_id),
                        "type": event.event_type,
                        "data": event.event_data or {},
                        "created_at": event.created_at.isoformat(),
                    }
                    for event in events
                ]

            if payloads:
                for item in payloads:
                    current_cursor = UUID(item["id"])
                    yield (
                        f"id: {item['id']}\n"
                        "event: ticket_update\n"
                        f"data: {json.dumps(item)}\n\n"
                    )
            else:
                yield ": heartbeat\n\n"

            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
