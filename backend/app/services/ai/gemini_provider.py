import json
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings


class GeminiProvider:
    def __init__(self):
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.llm_model

    def generate_json(
        self,
        *,
        system_prompt: str,
        input_data: dict[str, Any],
        temperature: float = 0.0,
        max_output_tokens: int = 150,
    ) -> dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.model,
            contents=json.dumps(
                input_data,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_mime_type="application/json",
            ),
        )

        if not response.text:
            raise ValueError("Gemini returned an empty response")

        result = json.loads(response.text)

        if not isinstance(result, dict):
            raise ValueError("Expected a JSON object")

        return result