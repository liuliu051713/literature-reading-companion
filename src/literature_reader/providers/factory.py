"""Provider construction isolated from the pipeline."""

from __future__ import annotations

from ..config import RunConfig
from .base import ModelProvider
from .gemini_provider import GeminiProvider
from .mock import MockProvider
from .openai_provider import OpenAIProvider


def create_provider(config: RunConfig) -> ModelProvider:
    if config.provider == "mock":
        return MockProvider()
    if config.provider == "openai":
        return OpenAIProvider(model=config.model)
    if config.provider == "gemini":
        return GeminiProvider(model=config.model)
    raise ValueError(f"Unsupported provider: {config.provider}")
