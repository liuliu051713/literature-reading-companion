"""OpenAI Responses API adapter.

The dependency is imported lazily so local/mock use does not require the
OpenAI SDK.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .base import ProviderConfigurationError, StructuredModelProvider


class OpenAIProvider(StructuredModelProvider):
    def __init__(self, model: str | None = None) -> None:
        self.model = model or "gpt-5.6"

    def _generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ProviderConfigurationError(
                "OPENAI_API_KEY is not set. Export it in your shell before choosing --provider openai."
            )
        try:
            from openai import OpenAI
        except ImportError as error:
            raise ProviderConfigurationError(
                "OpenAI support is not installed. Run: pip install -e '.[openai]'"
            ) from error

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        if not response.output_text:
            raise ValueError("OpenAI returned no structured text output.")
        return _parse_json(response.output_text, "OpenAI")


def _parse_json(raw: str, provider_name: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"{provider_name} returned invalid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{provider_name} returned a JSON value that is not an object.")
    return payload
