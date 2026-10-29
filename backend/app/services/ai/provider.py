from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    def generate_json(
        self,
        *,
        system_prompt: str,
        input_data: dict[str, Any],
        temperature: float = 0.0,
        max_output_tokens: int = 150,
    ) -> dict[str, Any]:
        """Generate and parse one JSON object from the configured LLM."""
        raise NotImplementedError
