from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.tickets import TicketStatus
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