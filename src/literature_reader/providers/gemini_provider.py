"""Gemini Interactions API adapter."""

from __future__ import annotations

import json
import os
from typing import Any

from .base import ProviderConfigurationError, StructuredModelProvider


class GeminiProvider(StructuredModelProvider):
    def __init__(self, model: str | None = None) -> None:
        self.model = model or "gemini-3.5-flash"

    def _generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ProviderConfigurationError(
                "GEMINI_API_KEY is not set. Export it in your shell before choosing --provider gemini."
            )
        try:
            from google import genai
        except ImportError as error:
            raise ProviderConfigurationError(
                "Gemini support is not installed. Run: pip install -e '.[gemini]'"
            ) from error

        client = genai.Client(api_key=api_key)
        interaction = client.interactions.create(
            model=self.model,
            input=f"{system}\n\n{prompt}",
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": schema,
            },
        )
        output_text = getattr(interaction, "output_text", None)
        if not output_text:
            raise ValueError("Gemini returned no structured text output.")
        return _parse_json(output_text)


def _parse_json(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"Gemini returned invalid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("Gemini returned a JSON value that is not an object.")
    return payload
