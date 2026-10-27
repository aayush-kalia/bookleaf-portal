
from datetime import date
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BookStage(str, PyEnum):
    MANUSCRIPT_RECEIVED = "Manuscript Received"
    EDITING = "Editing"
    COVER_DESIGN = "Cover Design"
    TYPESETTING = "Typesetting"
    PROOFREADING = "Proofreading"
    ISBN_ASSIGNMENT = "ISBN Assignment"
    PRINTING = "Printing"
    DISTRIBUTION_SETUP = "Distribution Setup"
    PUBLISHED_LIVE = "Published & Live"


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )
    author_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("authors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    isbn: Mapped[str | None] = mapped_column(String(20))
    genre: Mapped[str | None] = mapped_column(String(100))
    publication_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    stage: Mapped[BookStage | None] = mapped_column(
        Enum(BookStage, name="book_stage", values_callable=lambda enum: [
            item.value for item in enum
        ]),
        nullable=True,
    )
    mrp: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    royalty_per_copy: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2)
    )
    copies_sold: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    royalty_earned: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    royalty_paid: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    royalty_pending: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    last_payout_date: Mapped[date | None] = mapped_column(Date)
    print_partner: Mapped[str | None] = mapped_column(String(150))
    available_on: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
