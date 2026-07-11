"""Configuration values and validation for a reading run."""

from __future__ import annotations

from dataclasses import dataclass


VALID_PROVIDERS = {"mock", "openai", "gemini"}
VALID_TRANSLATIONS = {"none", "full"}
VALID_FORMATS = {"html", "docx", "all"}


@dataclass(frozen=True)
class RunConfig:
    provider: str = "mock"
    model: str | None = None
    translation: str = "none"
    annotation_depth: str = "deep"
    focus: tuple[str, ...] = (
        "research_question",
        "methods",
        "figures_tables",
        "results",
    )
    batch_size: int = 4

    def validate(self) -> None:
        if self.provider not in VALID_PROVIDERS:
            choices = ", ".join(sorted(VALID_PROVIDERS))
            raise ValueError(f"Unsupported provider '{self.provider}'. Choose one of: {choices}.")
        if self.translation not in VALID_TRANSLATIONS:
            choices = ", ".join(sorted(VALID_TRANSLATIONS))
            raise ValueError(f"Unsupported translation mode '{self.translation}'. Choose one of: {choices}.")
        if self.annotation_depth not in {"overview", "deep"}:
            raise ValueError("annotation_depth must be 'overview' or 'deep'.")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1.")
