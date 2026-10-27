
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, DbSession
from app.models.author import Author
from app.models.book import Book, BookStage
from app.schemas.book import (
    BookListResponse,
    BookResponse,
    RoyaltySummary,
)


router = APIRouter(prefix="/books", tags=["Books"])

ROYALTY_THRESHOLD = Decimal("1000.00")


def get_author_profile(db: Session, user_id) -> Author:
    author = db.scalar(
        select(Author).where(Author.user_id == user_id)
    )
    if author is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Author profile not found.",
        )
    return author


def is_published(book: Book) -> bool:
    return (
        book.stage == BookStage.PUBLISHED_LIVE
        or book.status.strip().lower() == "published & live"
    )


def visible_books(db: Session, user: CurrentUser) -> list[Book]:
    query = select(Book).order_by(Book.id)

    if user.role == "author":
        author = get_author_profile(db, user.id)
        query = query.where(Book.author_id == author.id)

    return list(db.scalars(query).all())


def calculate_royalty_summary(books: list[Book]) -> RoyaltySummary:
    published_books = [book for book in books if is_published(book)]

    earned = sum(
        (book.royalty_earned or Decimal("0.00") for book in published_books),
        Decimal("0.00"),
    )
    paid = sum(
        (book.royalty_paid or Decimal("0.00") for book in published_books),
        Decimal("0.00"),
    )
    pending = sum(
        (book.royalty_pending or Decimal("0.00") for book in published_books),
        Decimal("0.00"),
    )

    return RoyaltySummary(
        total_earned=earned,
        total_paid=paid,
        total_pending=pending,
        below_threshold=pending < ROYALTY_THRESHOLD,
    )


@router.get("", response_model=BookListResponse)
def list_books(
    db: DbSession,
    current_user: CurrentUser,
) -> BookListResponse:
    books = visible_books(db, current_user)

    return BookListResponse(
        books=[BookResponse.model_validate(book) for book in books],
        royalty_summary=calculate_royalty_summary(books),
    )


@router.get("/{book_id}", response_model=BookResponse)
def get_book(
    book_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> BookResponse:
    book = db.get(Book, book_id)

    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found.",
        )

    if current_user.role == "author":
        author = get_author_profile(db, current_user.id)
        if book.author_id != author.id:
            # Do not reveal that another author's book exists.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found.",
            )

    return BookResponse.model_validate(book)
