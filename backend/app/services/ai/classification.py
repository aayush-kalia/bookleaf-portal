
import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.provider import LLMProvider

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT_VERSION = "classify_v1"

Category = Literal[
    "royalty_payments",
    "isbn_metadata",
    "printing_quality",
    "distribution_availability",
    "production_status",
    "general_inquiry",
]
Priority = Literal["critical", "high", "medium", "low"]


class ClassificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Category
    priority: Priority
    reason: str = Field(min_length=1, max_length=500)


CLASSIFY_PROMPT_PATH = Path(__file__).parent / "prompts" / "classify_v1.txt"


def classify_ticket(
    ticket_data: dict[str, Any] | None = None,
    provider: LLMProvider | None = None,
    *,
    subject: str | None = None,
    description: str | None = None,
    book_context: str | None = None,
) -> ClassificationResult:
    """Classify ticket data. Keyword arguments remain supported for existing callers."""
    if ticket_data is None:
        ticket_data = {
            "subject": (subject or "")[:500],
            "description": (description or "")[:2000],
            "book_context": (book_context or "General / account level")[:300],
        }
    else:
        ticket_data = dict(ticket_data)
        if "description" in ticket_data and isinstance(ticket_data["description"], str):
            ticket_data["description"] = ticket_data["description"][:2000]
        if "subject" in ticket_data and isinstance(ticket_data["subject"], str):
            ticket_data["subject"] = ticket_data["subject"][:500]

    active_provider = provider or GeminiProvider()
    system_prompt = CLASSIFY_PROMPT_PATH.read_text(encoding="utf-8")

    result = active_provider.generate_json(
        system_prompt=system_prompt,
        input_data=ticket_data,
        temperature=0.0,
        max_output_tokens=150,
    )

    try:
        parsed = ClassificationResult.model_validate(result)
        if len(parsed.reason.split()) > 25:
            raise ValueError("Classification reason must be at most 25 words")
        return parsed
    except (ValidationError, ValueError):
        logger.warning("Gemini returned invalid classification output")
        raise
