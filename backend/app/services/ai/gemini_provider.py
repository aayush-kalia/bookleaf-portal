import json
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.ai.provider import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model

    def generate_json(
        self,
        *,
        system_prompt: str,
        input_data: dict[str, Any],
        temperature: float = 0.0,
        max_output_tokens: int = 500,
    ) -> dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.model,
            contents=json.dumps(
                input_data,
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            ),
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_mime_type="application/json",
            ),
        )

        content = response.text
        if not content:
            raise ValueError("Gemini returned an empty response")

        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("Expected the model response to be a JSON object")

        return parsed
