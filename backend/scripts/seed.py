
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.author import Author
from app.models.book import Book, BookStage
from app.models.user import User


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_ROOT / "bookleaf_sample_data.json"

AUTHOR_DEMO_PASSWORD = "Author@123"
ADMIN_DEMO_PASSWORD = "Admin@123"

ADMIN_ACCOUNTS = [
    ("admin1@bookleaf.test", "Admin One"),
    ("admin2@bookleaf.test", "Admin Two"),
    ("admin3@bookleaf.test", "Admin Three"),
]

STAGE_BY_STATUS = {
    "Published & Live": BookStage.PUBLISHED_LIVE,
    "In Production - Cover Design": BookStage.COVER_DESIGN,
    "In Production - Typesetting": BookStage.TYPESETTING,
}


def parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def decimal_value(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def load_and_validate_data() -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Seed data not found: {DATA_FILE}")

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    if not isinstance(data.get("authors"), list):
        raise ValueError("Expected a top-level 'authors' list.")

    author_ids = set()
    book_ids = set()
    total_books = 0

    for author in data["authors"]:
        author_id = author["author_id"]

        if author_id in author_ids:
            raise ValueError(f"Duplicate author ID: {author_id}")
        author_ids.add(author_id)

        for source_book in author.get("books", []):
            book_id = source_book["book_id"]

            if book_id in book_ids:
                raise ValueError(f"Duplicate book ID: {book_id}")
            book_ids.add(book_id)

            status = source_book["status"]
            if status not in STAGE_BY_STATUS:
                raise ValueError(
                    f"Unknown status {status!r} for book {book_id}"
                )

            copies = Decimal(str(source_book["total_copies_sold"]))
            earned = Decimal(str(source_book["total_royalty_earned"]))
            paid = Decimal(str(source_book["royalty_paid"]))
            pending = Decimal(str(source_book["royalty_pending"]))

            raw_per_copy = source_book.get("author_royalty_per_copy")

            if raw_per_copy is None:
                if status == "Published & Live":
                    raise ValueError(
                        f"Published book {book_id} has no per-copy royalty."
                    )
                per_copy = None
            else:
                per_copy = Decimal(str(raw_per_copy))

            if per_copy is not None and copies * per_copy != earned:
                raise ValueError(
                    f"Royalty calculation mismatch for {book_id}"
                )

            if paid + pending != earned:
                raise ValueError(
                    f"Paid + pending does not equal earned for {book_id}"
                )

            total_books += 1

    if len(author_ids) != 10 or total_books != 18:
        raise ValueError(
            f"Expected 10 authors and 18 books; found "
            f"{len(author_ids)} authors and {total_books} books."
        )

    return data


def get_or_create_user(
    db,
    *,
    email: str,
    name: str,
    role: str,
    password: str,
) -> User:
    normalized_email = email.strip().lower()
    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if user is None:
        user = User(
            email=normalized_email,
            name=name,
            role=role,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.flush()
    else:
        user.name = name
        user.role = role
        # Keep demo credentials deterministic across seed runs.
        user.password_hash = hash_password(password)

    return user


def seed() -> None:
    data = load_and_validate_data()

    with SessionLocal() as db:
        try:
            for email, name in ADMIN_ACCOUNTS:
                get_or_create_user(
                    db,
                    email=email,
                    name=name,
                    role="admin",
                    password=ADMIN_DEMO_PASSWORD,
                )

            author_count = 0
            book_count = 0

            for source_author in data["authors"]:
                user = get_or_create_user(
                    db,
                    email=source_author["email"],
                    name=source_author["name"],
                    role="author",
                    password=AUTHOR_DEMO_PASSWORD,
                )

                author = db.get(Author, source_author["author_id"])

                if author is None:
                    author = Author(
                        id=source_author["author_id"],
                        user_id=user.id,
                        name=source_author["name"],
                        email=source_author["email"],
                        phone=source_author.get("phone"),
                        city=source_author.get("city"),
                        joined_date=parse_date(
                            source_author.get("joined_date")
                        ),
                    )
                    db.add(author)
                else:
                    author.user_id = user.id
                    author.name = source_author["name"]
                    author.email = source_author["email"]
                    author.phone = source_author.get("phone")
                    author.city = source_author.get("city")
                    author.joined_date = parse_date(
                        source_author.get("joined_date")
                    )

                db.flush()
                author_count += 1

                for source_book in source_author.get("books", []):
                    book_id = source_book["book_id"]
                    book = db.get(Book, book_id)

                    values = {
                        "author_id": author.id,
                        "title": source_book["title"],
                        "isbn": source_book.get("isbn"),
                        "genre": source_book.get("genre"),
                        "publication_date": parse_date(
                            source_book.get("publication_date")
                        ),
                        "status": source_book["status"],
                        "stage": STAGE_BY_STATUS[source_book["status"]],
                        "mrp": decimal_value(source_book.get("mrp")),
                        "royalty_per_copy": decimal_value(
                            source_book.get("author_royalty_per_copy")
                        ),
                        "copies_sold": source_book["total_copies_sold"],
                        "royalty_earned": decimal_value(
                            source_book["total_royalty_earned"]
                        ),
                        "royalty_paid": decimal_value(
                            source_book["royalty_paid"]
                        ),
                        "royalty_pending": decimal_value(
                            source_book["royalty_pending"]
                        ),
                        "last_payout_date": parse_date(
                            source_book.get("last_royalty_payout_date")
                        ),
                        "print_partner": source_book.get("print_partner"),
                        "available_on": source_book.get("available_on"),
                    }

                    if book is None:
                        book = Book(id=book_id, **values)
                        db.add(book)
                    else:
                        for field, value in values.items():
                            setattr(book, field, value)

                    book_count += 1

            db.commit()
            print(
                f"Seed completed successfully: "
                f"{author_count} authors, {book_count} books, "
                f"{len(ADMIN_ACCOUNTS)} admins."
            )

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    seed()
