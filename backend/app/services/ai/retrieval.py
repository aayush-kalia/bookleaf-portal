from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.knowledge_base import KBChunk, KBExample


MAX_POLICY_CHARS = 2000


def retrieve_policy(
    db: Session,
    *,
    category: str,
    subject: str,
    description: str,
    limit: int = 2,
) -> list[dict]:
    """Return relevant category-specific/general policy chunks, bounded to 2 KB each."""
    limit = max(1, min(int(limit), 2))
    query_text = f"{subject[:500]} {description[:2000]}".strip()
    category_first = case((KBChunk.category == category, 0), else_=1)

    if query_text:
        query = func.plainto_tsquery("english", query_text)
        statement = (
            select(
                KBChunk.slug,
                KBChunk.title,
                KBChunk.content,
                func.ts_rank(KBChunk.search_vector, query).label("rank"),
            )
            .where(
                or_(KBChunk.category == category, KBChunk.category.is_(None)),
                KBChunk.search_vector.op("@@")(query),
            )
            .order_by(category_first, func.ts_rank(KBChunk.search_vector, query).desc())
            .limit(limit)
        )
        rows = db.execute(statement).all()
    else:
        rows = []

    # Fall back to category + general policy even when full-text search has no hits.
    if len(rows) < limit:
        existing_slugs = {row.slug for row in rows}
        fallback_stmt = (
            select(KBChunk.slug, KBChunk.title, KBChunk.content)
            .where(
                or_(KBChunk.category == category, KBChunk.category.is_(None)),
                KBChunk.slug.not_in(existing_slugs) if existing_slugs else True,
            )
            .order_by(category_first, KBChunk.title)
            .limit(limit - len(rows))
        )
        rows = list(rows) + list(db.execute(fallback_stmt).all())

    return [
        {
            "slug": row.slug,
            "title": row.title,
            "content": (row.content or "")[:MAX_POLICY_CHARS],
        }
        for row in rows
    ]


def retrieve_examples(
    db: Session,
    *,
    category: str,
    limit: int = 2,
) -> list[dict]:
    limit = max(1, min(int(limit), 2))
    rows = db.scalars(
        select(KBExample)
        .where(KBExample.category == category)
        .order_by(KBExample.id)
        .limit(limit)
    ).all()
    return [
        {
            "query": (row.author_query or "")[:1500],
            "expected_response": (row.expected_response or "")[:2000],
        }
        for row in rows
    ]
