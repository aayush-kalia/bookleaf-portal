import calendar
import logging
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.author import Author
from app.models.book import Book, BookStage
from app.models.knowledge_base import AIDraft, AIRun
from app.models.tickets.message import TicketMessage
from app.models.tickets.ticket import Ticket
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.retrieval import retrieve_examples, retrieve_policy

logger = logging.getLogger(__name__)

PROMPT_VERSION = "draft_v1"
PROMPT_PATH = Path(__file__).parent / "prompts" / "draft_system_v1.txt"
ROYALTY_THRESHOLD = Decimal("1000.00")
STAGE_ORDER = [stage.value for stage in BookStage]


def _text(value: Any, limit: int = 1500) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        value = value.value
    return str(value).strip()[:limit]


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _reference_date() -> date:
    raw = getattr(settings, "app_reference_date", "2026-01-15")
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw))
    except (TypeError, ValueError):
        logger.warning("Invalid APP_REFERENCE_DATE; using build-plan reference date")
        return date(2026, 1, 15)


def _quarter_start(value: date) -> date:
    return date(value.year, ((value.month - 1) // 3) * 3 + 1, 1)


def _quarter_end(value: date) -> date:
    start = _quarter_start(value)
    end_month = start.month + 2
    return date(start.year, end_month, calendar.monthrange(start.year, end_month)[1])


def _last_completed_quarter(reference: date) -> tuple[date, date]:
    current_start = _quarter_start(reference)
    last_day = current_start - timedelta(days=1)
    return _quarter_start(last_day), last_day


def _next_payout_due(reference: date) -> date:
    _, last_completed_end = _last_completed_quarter(reference)
    due = last_completed_end + timedelta(days=45)
    if due < reference:
        current_end = _quarter_end(reference)
        due = current_end + timedelta(days=45)
    return due


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value))


def _is_published(book: Book) -> bool:
    stage = getattr(book.stage, "value", book.stage)
    status = _text(book.status, 100).lower()
    return stage == BookStage.PUBLISHED_LIVE.value or status == "published & live"


def _book_facts(book: Book, *, include_financials: bool = True) -> dict[str, Any]:
    stage = _text(book.stage, 100) or _text(book.status, 100)
    result: dict[str, Any] = {
        "id": _text(book.id, 30),
        "title": _text(book.title, 200),
        "isbn": _text(book.isbn, 50) or None,
        "status": _text(book.status, 100),
        "stage": stage,
        "publication_date": _iso(book.publication_date),
        "print_partner": _text(book.print_partner, 150) or None,
        "available_on": list(book.available_on or []),
    }
    if not _is_published(book):
        result["financial_availability"] = "Available after publication"
        result["production_stage_order"] = STAGE_ORDER
        return result
    if include_financials:
        result.update({
            "mrp": _iso(book.mrp),
            "royalty_per_copy": _iso(book.royalty_per_copy),
            "copies_sold": book.copies_sold,
            "royalty_earned": _iso(book.royalty_earned),
            "royalty_paid": _iso(book.royalty_paid),
            "royalty_pending": _iso(book.royalty_pending),
            "last_payout_date": _iso(book.last_payout_date),
        })
    return result


def _build_facts(
    db: Session, ticket: Ticket, author: Author | None, book: Book | None
) -> dict[str, Any]:
    reference = _reference_date()
    books = list(db.scalars(select(Book).where(Book.author_id == ticket.author_id).order_by(Book.id)).all())
    published_books = [item for item in books if _is_published(item)]
    pending_total = sum((_decimal(item.royalty_pending) for item in published_books), Decimal("0.00"))
    last_quarter_start, last_quarter_end = _last_completed_quarter(reference)
    payout_due = _next_payout_due(reference)
    payout_dates = [item.last_payout_date for item in published_books if item.last_payout_date]
    latest_payout = max(payout_dates) if payout_dates else None
    has_eligible_published_book = any(
        item.publication_date is not None and item.publication_date <= last_quarter_end
        for item in published_books
    )
    payout_is_stale = latest_payout is None or latest_payout < last_quarter_start
    overdue = (
        pending_total >= ROYALTY_THRESHOLD
        and payout_is_stale
        and has_eligible_published_book
    )

    facts: dict[str, Any] = {
        "reference_date": reference.isoformat(),
        "author": {
            "id": _text(getattr(author, "id", ""), 30),
            "name": _text(getattr(author, "name", ""), 150),
            "email": _text(getattr(author, "email", ""), 200),
            "joined_date": _iso(getattr(author, "joined_date", None)),
        },
        "royalty_account": {
            "pending_total": str(pending_total.quantize(Decimal("0.01"))),
            "threshold": str(ROYALTY_THRESHOLD),
            "below_threshold": pending_total < ROYALTY_THRESHOLD,
            "next_payout_due": payout_due.isoformat(),
            "latest_payout_date": _iso(latest_payout),
            "overdue": overdue,
            "calculation_note": (
                "Overdue is an estimate because the supplied sample data has no per-quarter sales ledger."
            ),
        },
        "books": [_book_facts(item) for item in books],
    }
    facts["ticket_book"] = _book_facts(book) if book is not None else None
    return facts


def _latest_author_message(db: Session, ticket_id: Any) -> TicketMessage | None:
    return db.scalar(
        select(TicketMessage)
        .where(
            TicketMessage.ticket_id == ticket_id,
            TicketMessage.sender_role == "author",
        )
        .order_by(TicketMessage.created_at.desc(), TicketMessage.id.desc())
        .limit(1)
    )


def _cache_is_current(
    latest_author_message: TicketMessage | None,
    cached_draft: AIDraft | None,
) -> bool:
    if cached_draft is None:
        return False
    latest_id = latest_author_message.id if latest_author_message else None
    return cached_draft.based_on_message_id == latest_id


def _build_conversation(db: Session, ticket: Ticket) -> list[dict[str, str]]:
    # Internal notes use a separate table and are deliberately never queried here.
    messages = db.scalars(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket.id)
        .order_by(TicketMessage.created_at.desc(), TicketMessage.id.desc())
        .limit(5)
    ).all()
    messages = list(reversed(messages))
    conversation = [{
        "role": "author",
        "message": (
            f"Original ticket subject: {_text(ticket.subject, 500)}\n"
            f"Original ticket description: {_text(ticket.description, 1500)}"
        ),
    }]
    for message in messages:
        conversation.append({
            "role": _text(message.sender_role, 30) or "unknown",
            "message": _text(message.body, 1500),
        })
    return conversation


def _validate_result(result: dict[str, Any]) -> dict[str, Any]:
    if set(result) != {"draft", "missing_info", "needs_escalation", "escalation_reason"}:
        raise ValueError("AI draft output must contain exactly the four required fields")
    draft = result["draft"]
    missing_info = result["missing_info"]
    needs_escalation = result["needs_escalation"]
    escalation_reason = result["escalation_reason"]
    if not isinstance(draft, str) or not draft.strip():
        raise ValueError("AI response is missing a valid draft")
    words = draft.strip().split()
    if not 90 <= len(words) <= 180:
        raise ValueError("AI draft must contain 90–180 words")
    if not isinstance(missing_info, list) or not all(isinstance(item, str) and item.strip() for item in missing_info):
        raise ValueError("AI response has invalid missing_info")
    if not isinstance(needs_escalation, bool):
        raise ValueError("AI response has invalid needs_escalation")
    if escalation_reason is not None and not isinstance(escalation_reason, str):
        raise ValueError("AI response has invalid escalation_reason")
    if needs_escalation and not (escalation_reason or "").strip():
        raise ValueError("escalation_reason is required when escalation is needed")
    return {
        "draft": draft.strip(),
        "missing_info": missing_info,
        "needs_escalation": needs_escalation,
        "escalation_reason": escalation_reason.strip() if isinstance(escalation_reason, str) else None,
    }


def _failure_status(exc: Exception) -> str:
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "ratelimit" in name or "rate_limit" in name:
        return "rate_limited"
    if isinstance(exc, (ValueError, TypeError)):
        return "invalid_output"
    return "error"


def get_or_generate_draft(
    db: Session,
    *,
    ticket: Ticket,
    force_regenerate: bool = False,
) -> dict[str, Any]:
    cached = db.get(AIDraft, ticket.id)
    latest_author_message = _latest_author_message(db, ticket.id)

    if cached is not None and not force_regenerate and _cache_is_current(latest_author_message, cached):
        return {**cached.content, "cached": True, "ai_available": True}

    author = db.get(Author, ticket.author_id)
    book = db.get(Book, ticket.book_id) if ticket.book_id else None
    category = _text(ticket.category, 50)
    policy = retrieve_policy(
        db,
        category=category,
        subject=_text(ticket.subject, 500),
        description=_text(ticket.description, 2000),
        limit=2,
    )
    examples = retrieve_examples(db, category=category, limit=2)
    input_data = {
        "ticket": {
            "code": _text(ticket.ticket_code, 50),
            "subject": _text(ticket.subject, 500),
            "description": _text(ticket.description, 2000),
            "category": category,
            "priority": _text(ticket.priority, 20),
            "status": _text(ticket.status, 20),
        },
        "facts": _build_facts(db, ticket, author, book),
        "conversation": _build_conversation(db, ticket),
        "policy_excerpts": policy,
        "response_examples": examples,
    }

    started = time.perf_counter()
    run = AIRun(
        ticket_id=ticket.id,
        kind="draft",
        model=settings.gemini_model,
        prompt_version=PROMPT_VERSION,
        status="error",
    )
    db.add(run)
    db.flush()

    try:
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        result = _validate_result(
            GeminiProvider().generate_json(
                system_prompt=system_prompt,
                input_data=input_data,
                temperature=0.2,
                max_output_tokens=700,
            )
        )
        run.status = "success"
        run.latency_ms = int((time.perf_counter() - started) * 1000)

        if cached is None:
            cached = AIDraft(
                ticket_id=ticket.id,
                content=result,
                based_on_message_id=latest_author_message.id if latest_author_message else None,
                prompt_version=PROMPT_VERSION,
                ai_run_id=run.id,
            )
            db.add(cached)
        else:
            cached.content = result
            cached.based_on_message_id = latest_author_message.id if latest_author_message else None
            cached.prompt_version = PROMPT_VERSION
            cached.ai_run_id = run.id

        db.commit()
        db.refresh(cached)
        return {**result, "cached": False, "ai_available": True}

    except Exception as exc:
        run.status = _failure_status(exc)
        # Avoid writing request bodies, credentials, or provider response payloads to logs.
        run.error_message = f"{type(exc).__name__}: AI draft generation failed"[:500]
        run.latency_ms = int((time.perf_counter() - started) * 1000)
        db.commit()
        logger.exception("Draft generation failed for ticket %s (%s)", ticket.ticket_code, run.status)

        if cached is not None:
            return {**cached.content, "cached": True, "ai_available": False}

        # Existing response shape lets the UI keep manual reply available on AI failure.
        return {
            "draft": (
                "Thank you for contacting BookLeaf Author Support. "
                "We are reviewing your concern and will verify the "
                "relevant details before confirming the next steps.\n\n"
                "BookLeaf Author Support"
            ),
            "missing_info": [
                "Review the author's concern and verify the relevant details."
            ],
            "needs_escalation": True,
            "escalation_reason": (
                "AI drafting was unavailable; manual review is required."
            ),
            "cached": False,
            "ai_available": False,
        }
