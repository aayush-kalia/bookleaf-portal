
import re


def classify_with_rules(subject: str, description: str) -> dict[str, str]:
    text = f"{subject} {description}".lower()
    text = re.sub(r"\s+", " ", text).strip()

    def has_any(*keywords: str) -> bool:
        return any(keyword in text for keyword in keywords)

    # ISBN errors are explicitly high-priority in the assignment.
    if has_any(
        "wrong isbn",
        "incorrect isbn",
        "duplicate isbn",
        "isbn error",
        "different isbn",
        "isbn mismatch",
        "wrong book linked",
        "incorrect book linked",
    ):
        return {
            "category": "isbn_metadata",
            "priority": "high",
            "reason": "ISBN or book-linking errors require production-team escalation.",
        }

    # Serious or prolonged royalty delays.
    prolonged_royalty_delay = (
        has_any("royalty", "royalties", "payout", "payment")
        and (
            has_any("6 months", "six months", "6 month", "six-month")
            or (
                has_any("overdue", "over 45 days", "more than 45 days")
                and has_any("royalty", "royalties", "payout", "payment")
            )
        )
    )

    if prolonged_royalty_delay:
        return {
            "category": "royalty_payments",
            "priority": "high",
            "reason": "A prolonged or overdue royalty payment requires investigation.",
        }

    # Printing defects may require verification and a free reprint.
    if has_any(
        "printing quality",
        "print quality",
        "misprint",
        "misprints",
        "binding defect",
        "binding defects",
        "blurry pages",
        "blurry images",
        "damaged copies",
        "pages are misaligned",
        "color inconsistency",
        "colour inconsistency",
    ):
        return {
            "category": "printing_quality",
            "priority": "high",
            "reason": "A reported printing defect requires verification.",
        }

    # Royalty calculation and statement questions are not automatically urgent.
    if has_any(
        "royalty",
        "royalties",
        "royalty statement",
        "royalty breakdown",
        "royalty calculation",
        "royalty amount",
        "royalty paid",
        "royalty pending",
        "payout",
    ):
        return {
            "category": "royalty_payments",
            "priority": "medium",
            "reason": "A royalty or payout query requires review of the applicable figures and payment cycle.",
        }

    # Distribution and availability issues.
    if has_any(
        "currently unavailable",
        "book unavailable",
        "not available on amazon",
        "not available on flipkart",
        "stock sync",
        "stock synchronization",
        "stock synchronisation",
        "distribution issue",
        "retailer listing",
        "listing not live",
        "book not listed",
    ):
        return {
            "category": "distribution_availability",
            "priority": "medium",
            "reason": "A distribution or listing issue may require a stock re-sync.",
        }

    # Production status and progress queries.
    if has_any(
        "cover design",
        "typesetting",
        "proofreading",
        "manuscript",
        "production status",
        "production update",
        "book status",
        "publication status",
        "publishing status",
        "publication delayed",
        "production delayed",
    ):
        return {
            "category": "production_status",
            "priority": "medium",
            "reason": "The book's production stage and any outstanding steps need to be checked.",
        }

    # ISBN metadata requests that aren't errors.
    if has_any("isbn", "metadata", "book description", "author bio", "author biography"):
        return {
            "category": "isbn_metadata" if has_any("isbn", "metadata") else "general_inquiry",
            "priority": "low",
            "reason": "This appears to be a routine metadata update request.",
        }

    return {
        "category": "general_inquiry",
        "priority": "low",
        "reason": "No specific high-priority issue matched the fallback rules.",
    }
