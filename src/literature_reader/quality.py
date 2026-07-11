"""Validation that protects source-to-annotation correspondence."""

from __future__ import annotations

from collections import Counter
import re

from .config import RunConfig
from .models import Annotation, ReadingCopy


class AnnotationQualityError(ValueError):
    """Raised when a reading copy would misrepresent source-to-note alignment."""


_DEEP_EXPLANATION_MINIMUM = 100
_NAVIGATION_ONLY_PREFIX = re.compile(r"^(?:本段|该段|这一段|这里)?(?:作用|衔接|要点|边界)[：:]")


def validate_annotation_detail(annotation: Annotation, annotation_depth: str = "deep") -> None:
    """Reject a deep-reading note that is only a short navigation summary.

    Anchor validity and nonempty fields are necessary, but they cannot stop a
    provider from returning five labels with almost no explanation.  Deep mode
    therefore requires a connected explanation long enough to teach the
    passage and at least two sentence-like clauses.  Overview mode keeps the
    original lightweight behaviour for users who intentionally ask for it.
    """

    if annotation_depth != "deep":
        return
    compact = re.sub(r"\s+", "", annotation.explanation)
    if len(compact) < _DEEP_EXPLANATION_MINIMUM:
        raise AnnotationQualityError(
            f"{annotation.anchor} explanation is too short for deep reading. "
            f"Provide at least {_DEEP_EXPLANATION_MINIMUM} non-whitespace characters that explain "
            "the passage itself for a beginner."
        )
    if _NAVIGATION_ONLY_PREFIX.match(compact):
        raise AnnotationQualityError(
            f"{annotation.anchor} explanation starts as a navigation label. "
            "Use role and context for navigation; use explanation for the substantive meaning."
        )
    if len(re.findall(r"[。！？!?；;]", compact)) < 2:
        raise AnnotationQualityError(
            f"{annotation.anchor} explanation needs at least two connected sentences or clauses in deep mode."
        )


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
            continue
        try:
            validate_annotation_detail(annotation, config.annotation_depth)
        except AnnotationQualityError as error:
            errors.append(str(error))

    if errors:
        raise AnnotationQualityError(" ".join(errors))

    warnings = list(reading_copy.warnings)
    if len(actual) != len(expected):
        warnings.append("Annotation order was normalised by source anchor before rendering.")
    return tuple(warnings)
