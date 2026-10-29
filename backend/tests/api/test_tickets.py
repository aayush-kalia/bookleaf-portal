from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.main import app
from app.models.tickets import (
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from app.services import ticket_service
from app.services.ticket_service import ensure_ticket_access


@pytest.fixture
def ticket():
    return SimpleNamespace(
        id=uuid4(),
        author_id="AUTH001",
        status=TicketStatus.OPEN,
    )


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def client_overrides():
    """Install and reliably clear dependency overrides for API tests."""
    yield
    app.dependency_overrides.clear()


def test_author_can_access_own_ticket(db, ticket):
    db.scalar.return_value = SimpleNamespace(id="AUTH001")
    author = SimpleNamespace(id=uuid4(), role="author")

    ensure_ticket_access(db, author, ticket)


def test_author_cannot_access_another_authors_ticket(db, ticket):
    db.scalar.return_value = SimpleNamespace(id="AUTH002")
    author = SimpleNamespace(id=uuid4(), role="author")

    with pytest.raises(HTTPException) as exc:
        ensure_ticket_access(db, author, ticket)

    assert exc.value.status_code == 404


def test_admin_can_access_any_ticket(db, ticket):
    admin = SimpleNamespace(id=uuid4(), role="admin")

    ensure_ticket_access(db, admin, ticket)

    db.scalar.assert_not_called()


def test_unknown_role_cannot_access_ticket(db, ticket):
    user = SimpleNamespace(id=uuid4(), role="unknown")

    with pytest.raises(HTTPException) as exc:
        ensure_ticket_access(db, user, ticket)

    assert exc.value.status_code == 404


def _classification_ticket():
    return SimpleNamespace(
        id=uuid4(),
        ticket_code="TKT-TEST",
        ai_category=None,
        ai_priority=None,
        ai_reason=None,
        classification_source="default",
        ai_status="pending",
        category=TicketCategory.GENERAL_INQUIRY,
        priority=TicketPriority.MEDIUM,
    )


def _patch_background_dependencies(monkeypatch, db):
    monkeypatch.setattr(ticket_service, "SessionLocal", lambda: db)

def test_background_classification_persists_ai_result(monkeypatch):
    ticket = _classification_ticket()
    db = MagicMock()
    db.get.return_value = ticket
    _patch_background_dependencies(monkeypatch, db)

    monkeypatch.setattr(
        ticket_service,
        "classify_ticket",
        lambda data: SimpleNamespace(
            category="royalty_payments",
            priority="high",
            reason="Royalty payment requires investigation.",
        ),
    )

    ticket_service.classify_ticket_background(
        str(ticket.id),
        "Missing royalty payment",
        "My royalty payment has not arrived.",
    )

    assert ticket.category == TicketCategory.ROYALTY_PAYMENTS
    assert ticket.priority == TicketPriority.HIGH
    assert ticket.ai_category == TicketCategory.ROYALTY_PAYMENTS.value
    assert ticket.ai_priority == TicketPriority.HIGH.value
    assert ticket.ai_reason == "Royalty payment requires investigation."
    assert ticket.classification_source == "ai"
    assert ticket.ai_status == "done"
    db.commit.assert_called_once()
    db.rollback.assert_not_called()
    db.close.assert_called_once()


def test_background_classification_persists_rule_fallback(monkeypatch):
    ticket = _classification_ticket()
    db = MagicMock()
    db.get.return_value = ticket
    _patch_background_dependencies(monkeypatch, db)

    monkeypatch.setattr(
        ticket_service,
        "classify_ticket",
        lambda data: (_ for _ in ()).throw(
            RuntimeError("AI unavailable")
        ),
    )

    monkeypatch.setattr(
        ticket_service,
        "classify_with_rules",
        lambda subject, description: {
            "category": "isbn_metadata",
            "priority": "high",
            "reason": "ISBN discrepancy requires investigation.",
        },
    )

    ticket_service.classify_ticket_background(
        str(ticket.id),
        "Incorrect ISBN",
        "The ISBN on the retailer listing is incorrect.",
    )

    assert ticket.category == TicketCategory.ISBN_METADATA
    assert ticket.priority == TicketPriority.HIGH
    assert ticket.ai_category == TicketCategory.ISBN_METADATA.value
    assert ticket.ai_priority == TicketPriority.HIGH.value
    assert ticket.ai_reason == "ISBN discrepancy requires investigation."
    assert ticket.classification_source == "rules"
    assert ticket.ai_status == "failed"
    db.commit.assert_called_once()
    db.rollback.assert_not_called()
    db.close.assert_called_once()


def test_background_classification_uses_safe_defaults_when_both_methods_fail(
    monkeypatch, caplog
):
    ticket = _classification_ticket()
    db = MagicMock()
    db.get.return_value = ticket
    _patch_background_dependencies(monkeypatch, db)

    monkeypatch.setattr(
        ticket_service,
        "classify_ticket",
        lambda data: (_ for _ in ()).throw(
            RuntimeError("AI unavailable")
        ),
    )

    monkeypatch.setattr(
        ticket_service,
        "classify_with_rules",
        lambda subject, description: (_ for _ in ()).throw(
            RuntimeError("Rules unavailable")
        ),
    )

    with caplog.at_level(logging.ERROR):
        ticket_service.classify_ticket_background(
            str(ticket.id),
            "Unknown issue",
            "Description of the issue.",
        )

    assert ticket.category == TicketCategory.GENERAL_INQUIRY
    assert ticket.priority == TicketPriority.MEDIUM
    assert ticket.ai_category == TicketCategory.GENERAL_INQUIRY.value
    assert ticket.ai_priority == TicketPriority.MEDIUM.value
    assert ticket.ai_reason == "AI and rule-based classification both failed."
    assert ticket.classification_source == "rules"
    assert ticket.ai_status == "failed"
    assert "Rule-based classification failed" in caplog.text
    db.commit.assert_called_once()
    db.close.assert_called_once()


def test_background_classification_skips_missing_ticket(monkeypatch, caplog):
    db = MagicMock()
    db.get.return_value = None
    _patch_background_dependencies(monkeypatch, db)

    with caplog.at_level(logging.ERROR):
        ticket_service.classify_ticket_background(
            str(uuid4()),
            "Missing ticket",
            "This ticket does not exist.",
        )

    assert "Classification skipped" in caplog.text
    db.commit.assert_not_called()
    db.close.assert_called_once()


def test_background_classification_rolls_back_when_persistence_fails(monkeypatch):
    ticket = _classification_ticket()
    db = MagicMock()
    db.get.return_value = ticket
    db.commit.side_effect = RuntimeError("Database unavailable")

    _patch_background_dependencies(monkeypatch, db)

    monkeypatch.setattr(
        ticket_service,
        "classify_ticket",
        lambda data: SimpleNamespace(
            category="royalty_payments",
            priority="high",
            reason="Royalty payment requires investigation.",
        ),
    )

    ticket_service.classify_ticket_background(
        str(ticket.id),
        "Missing royalty payment",
        "My royalty payment has not arrived.",
    )

    db.commit.assert_called_once()
    db.rollback.assert_called_once()
    db.close.assert_called_once()


def test_create_ticket_triggers_background_classification(monkeypatch, client_overrides):
    user_id = uuid4()
    author = SimpleNamespace(id="AUTH001", user_id=user_id)
    user = SimpleNamespace(id=user_id, role="author", author_id="AUTH001")
    db = MagicMock()
    db.scalar.return_value = author
    db.get.return_value = None

    now = datetime.now(timezone.utc)

    def fake_create_ticket(*args, **kwargs):
        return SimpleNamespace(
            id=uuid4(),
            ticket_code="TKT-TEST",
            author_id="AUTH001",
            book_id=None,
            subject="Missing royalty payment",
            description="My royalty payment has not arrived.",
            status=TicketStatus.OPEN,
            category=TicketCategory.ROYALTY_PAYMENTS,
            priority=TicketPriority.HIGH,
            classification_source="default",
            ai_status="pending",
            ai_category=None,
            ai_priority=None,
            ai_reason=None,
            assigned_admin_id=None,
            last_author_message_at=None,
            created_at=now,
            updated_at=now,
            resolved_at=None,
            closed_at=None,
        )

    monkeypatch.setattr(
        "app.api.v1.tickets.service.create_ticket",
        fake_create_ticket,
    )

    background_called = {}

    def fake_classify(ticket_id, subject, description, book_context=""):
        background_called["ticket_id"] = ticket_id
        background_called["subject"] = subject
        background_called["description"] = description
        background_called["book_context"] = book_context

    monkeypatch.setattr(
        "app.api.v1.tickets.classify_ticket_background",
        fake_classify,
    )

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/tickets",
            json={
                "subject": "Missing royalty payment",
                "description": "My royalty payment has not arrived.",
            },
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert background_called["subject"] == "Missing royalty payment"
    assert background_called["description"] == "My royalty payment has not arrived."
    assert background_called["ticket_id"] == payload["id"]
    assert payload["classification_source"] == "default"
    assert payload["ai_status"] == "pending"
    assert payload["ai_category"] is None
    assert payload["ai_priority"] is None
    assert payload["ai_reason"] is None
