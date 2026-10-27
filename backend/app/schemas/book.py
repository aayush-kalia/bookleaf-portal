
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BookResponse(BaseModel):
    id: str
    author_id: str
    title: str
    isbn: str | None
    genre: str | None
    publication_date: date | None
    status: str
    stage: str | None
    mrp: Decimal | None
    royalty_per_copy: Decimal | None
    copies_sold: int
    royalty_earned: Decimal
    royalty_paid: Decimal
    royalty_pending: Decimal
    last_payout_date: date | None
    print_partner: str | None
    available_on: list[str] | None

    model_config = ConfigDict(from_attributes=True)


class RoyaltySummary(BaseModel):
    total_earned: Decimal
    total_paid: Decimal
    total_pending: Decimal
    below_threshold: bool


class BookListResponse(BaseModel):
    books: list[BookResponse]
    royalty_summary: RoyaltySummary
