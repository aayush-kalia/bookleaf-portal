
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.session import SessionLocal
from app.models.knowledge_base import KBChunk, KBExample


CHUNKS = [
    {
        "slug": "company-overview",
        "category": None,
        "title": "Company overview and publishing packages",
        "content": (
            "BookLeaf Publishing operates in India and the US. Packages include "
            "Standard Free with no upfront cost and Bestseller Breakthrough, a "
            "premium package with marketing and distribution add-ons. BookLeaf "
            "handles cover design, typesetting, ISBN assignment, printing, "
            "distribution and royalty management. Its in-house printing facility "
            "and warehouse are in Delhi. Print partners include Repro India "
            "and Epitome Books."
        ),
    },
    {
        "slug": "royalty-calculation",
        "category": "royalty_payments",
        "title": "Royalty calculation",
        "content": (
            "The author receives 80% of net profit and BookLeaf receives 20%. "
            "Net profit equals MRP minus printing cost, platform commission "
            "and shipping charges. Authors can view a detailed royalty "
            "breakdown by sales platform in their dashboard."
        ),
    },
    {
        "slug": "royalty-schedule",
        "category": "royalty_payments",
        "title": "Royalty schedule and payout threshold",
        "content": (
            "Royalties are calculated quarterly and paid within 45 days after "
            "the quarter ends. The minimum payout is INR 1000. Amounts below "
            "the threshold roll over to the next quarter. Payouts are made by "
            "bank transfer to the account linked in the author's dashboard. "
            "Check linked bank details before assuming a payout is ready."
        ),
    },
    {
        "slug": "isbn-policy",
        "category": "isbn_metadata",
        "title": "ISBN assignment and errors",
        "content": (
            "Each book published through BookLeaf receives a unique ISBN under "
            "BookLeaf's publisher imprint. Authors wanting their own imprint "
            "must obtain their ISBN independently. Duplicate, incorrect or "
            "mismatched ISBN reports are high-priority issues escalated to "
            "the production team. The team should investigate and respond "
            "within 48 hours."
        ),
    },
    {
        "slug": "metadata-updates",
        "category": None,
        "title": "Author descriptions and metadata updates",
        "content": (
            "Authors can request book description and metadata updates through "
            "the dashboard or email. Changes typically appear within 3–5 "
            "business days."
        ),
    },
    {
        "slug": "printing-quality",
        "category": "printing_quality",
        "title": "Printing quality and turnaround",
        "content": (
            "Most printing is handled in-house. Overflow or specific format "
            "requirements may be handled by Repro India or Epitome Books. "
            "Standard printing turnaround is 5–7 business days from order "
            "confirmation. Verified misprints, binding defects or colour "
            "inconsistency qualify for a free reprint. Photos of defective "
            "copies may be requested for verification."
        ),
    },
    {
        "slug": "distribution",
        "category": "distribution_availability",
        "title": "Distribution and unavailable listings",
        "content": (
            "BookLeaf distributes through Amazon India, Flipkart, Amazon US, "
            "Amazon UK and the BookLeaf Store. New listings typically go live "
            "within 7–10 business days after publication is complete. An "
            "unavailable listing usually indicates a stock synchronisation "
            "issue. The team can trigger a resync within 24–48 hours."
        ),
    },
    {
        "slug": "production-stages",
        "category": "production_status",
        "title": "Book production stages",
        "content": (
            "Production stages are Manuscript Received, Editing if opted, "
            "Cover Design, Typesetting, Proofreading, ISBN Assignment, Printing, "
            "Distribution Setup, and Published & Live. Authors receive email "
            "updates at each stage. Common delays occur while waiting for "
            "author approval at Cover Design or during proofreading revisions."
        ),
    },
]


EXAMPLES = [
    {
        "category": "royalty_payments",
        "author_query": "I published my book 4 months ago and still haven't received any royalty. What's going on?",
        "expected_response": (
            "Acknowledge the concern. Explain quarterly calculations and the "
            "45-day payout window. Check linked bank details and the specific "
            "next payout date. If overdue, escalate with a 48-hour timeline."
        ),
    },
    {
        "category": "royalty_payments",
        "author_query": "My royalty seems too low. I sold 200 copies but only received INR 3000.",
        "expected_response": (
            "Explain the net-profit calculation and offer a line-by-line "
            "breakdown by sales platform. Do not invent missing cost figures."
        ),
    },
    {
        "category": "isbn_metadata",
        "author_query": "My book shows a different ISBN on Amazon than on the physical copy.",
        "expected_response": (
            "Acknowledge the serious mismatch, mark it high priority and "
            "escalate to production. Give the author a 48-hour update timeline."
        ),
    },
    {
        "category": "printing_quality",
        "author_query": "My printed copies have blurry images and poor binding.",
        "expected_response": (
            "Acknowledge the quality issue. Request photos if needed and "
            "explain that a free reprint can be arranged after verification."
        ),
    },
    {
        "category": "distribution_availability",
        "author_query": "My published book is unavailable on Amazon.",
        "expected_response": (
            "Explain that this usually indicates a stock-sync issue and "
            "that the team can trigger a resync within 24–48 hours."
        ),
    },
    {
        "category": "production_status",
        "author_query": "Why is my book stuck at cover design?",
        "expected_response": (
            "Use the actual book status if available. Explain that author "
            "approval can cause delays and state the next step without guessing."
        ),
    },
    {
        "category": "general_inquiry",
        "author_query": "Can I update my author bio?",
        "expected_response": (
            "Explain the available dashboard or email route and the typical "
            "3–5 business-day timeframe for metadata changes."
        ),
    },
]


def upsert_chunks(db):
    for item in CHUNKS:
        existing = db.scalar(
            select(KBChunk).where(KBChunk.slug == item["slug"])
        )
        if existing:
            existing.category = item["category"]
            existing.title = item["title"]
            existing.content = item["content"]
        else:
            db.add(KBChunk(**item))


def upsert_examples(db):
    for item in EXAMPLES:
        existing = db.scalar(
            select(KBExample).where(
                KBExample.category == item["category"],
                KBExample.author_query == item["author_query"],
            )
        )
        if existing:
            existing.expected_response = item["expected_response"]
        else:
            db.add(KBExample(**item))


def main():
    with SessionLocal() as db:
        try:
            upsert_chunks(db)
            upsert_examples(db)
            db.commit()
            print(
                f"Knowledge Base loaded: {len(CHUNKS)} sections, "
                f"{len(EXAMPLES)} examples."
            )
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
