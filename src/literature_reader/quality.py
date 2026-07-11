"""Validation that protects source-to-annotation correspondence."""

from __future__ import annotations

from collections import Counter

from .config import RunConfig
from .models import ReadingCopy


class AnnotationQualityError(ValueError):
    """Raised when a reading copy would misrepresent source-to-note alignment."""


def validate_reading_copy(reading_copy: ReadingCopy, config: RunConfig) -> tuple[str, ...]:
    expected = [paragraph.anchor for paragraph in reading_copy.source.paragraphs]
    actual = [annotation.anchor for annotation in reading_copy.annotations]
    expected_set = set(expected)
    actual_set = set(actual)
    errors: list[str] = []

    duplicates = sorted(anchor for anchor, count in Counter(actual).items() if count > 1)
    if duplicates:
        errors.append(f"Duplicate annotation anchors: {', '.join(duplicates)}.")

    missing = sorted(expected_set - actual_set)
    if missing:
        errors.append(f"Missing annotations for: {', '.join(missing)}.")

    unknown = sorted(actual_set - expected_set)
    if unknown:
        errors.append(f"Annotations refer to unknown source anchors: {', '.join(unknown)}.")

    if config.translation == "full":
        untranslated = [annotation.anchor for annotation in reading_copy.annotations if not annotation.translation]
        if untranslated:
            errors.append(f"Translation mode is full but these anchors have no translation: {', '.join(untranslated)}.")

    for annotation in reading_copy.annotations:
        required_fields = {
            "role": annotation.role,
            "context": annotation.context,
            "explanation": annotation.explanation,
            "takeaway": annotation.takeaway,
            "caveat": annotation.caveat,
        }
        empty = [name for name, value in required_fields.items() if not value.strip()]
        if empty:
            errors.append(f"{annotation.anchor} has empty required fields: {', '.join(empty)}.")

    if errors:
        raise AnnotationQualityError(" ".join(errors))

    warnings = list(reading_copy.warnings)
    if len(actual) != len(expected):
        warnings.append("Annotation order was normalised by source anchor before rendering.")
    return tuple(warnings)
