"""Shared provider interface and structured-output helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..config import RunConfig
from ..models import Annotation, FocusPoint, PaperMap, Paragraph, SourceDocument
from ..prompts import (
    ANNOTATION_SYSTEM_PROMPT,
    PAPER_MAP_SYSTEM_PROMPT,
    build_annotation_prompt,
    build_paper_map_prompt,
)
from ..schema import PAPER_MAP_SCHEMA, annotation_response_schema


class ProviderConfigurationError(RuntimeError):
    """Raised when a selected model provider is not installed or configured."""


class ModelProvider(ABC):
    """A provider that returns source-linked structured reading data."""

    @abstractmethod
    def build_paper_map(self, document: SourceDocument) -> PaperMap:
        raise NotImplementedError

    @abstractmethod
    def annotate(
        self,
        paper_map: PaperMap,
        paragraphs: tuple[Paragraph, ...],
        config: RunConfig,
        previous: Paragraph | None,
        following: Paragraph | None,
    ) -> tuple[Annotation, ...]:
        raise NotImplementedError


class StructuredModelProvider(ModelProvider):
    """Base class for providers with JSON-schema-constrained responses."""

    @abstractmethod
    def _generate_json(self, *, system: str, prompt: str, schema_name: str, schema: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def build_paper_map(self, document: SourceDocument) -> PaperMap:
        payload = self._generate_json(
            system=PAPER_MAP_SYSTEM_PROMPT,
            prompt=build_paper_map_prompt(document),
            schema_name="paper_map",
            schema=PAPER_MAP_SCHEMA,
        )
        return PaperMap(
            title=_required_text(payload, "title"),
            research_question=_required_text(payload, "research_question"),
            central_claim=_required_text(payload, "central_claim"),
            argument_map=tuple(_required_list_of_text(payload, "argument_map")),
            scope_notes=_required_text(payload, "scope_notes"),
        )

    def annotate(
        self,
        paper_map: PaperMap,
        paragraphs: tuple[Paragraph, ...],
        config: RunConfig,
        previous: Paragraph | None,
        following: Paragraph | None,
    ) -> tuple[Annotation, ...]:
        payload = self._generate_json(
            system=ANNOTATION_SYSTEM_PROMPT,
            prompt=build_annotation_prompt(paper_map, paragraphs, config, previous, following),
            schema_name="source_linked_annotations",
            schema=annotation_response_schema(),
        )
        raw_annotations = payload.get("annotations")
        if not isinstance(raw_annotations, list):
            raise ValueError("Provider response must contain an 'annotations' list.")
        return tuple(_annotation_from_payload(item) for item in raw_annotations)


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Provider response field '{key}' must be a non-empty string.")
    return value.strip()


def _required_list_of_text(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"Provider response field '{key}' must be a non-empty list.")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"Provider response field '{key}' must contain non-empty strings.")
    return [item.strip() for item in value]


def _annotation_from_payload(item: Any) -> Annotation:
    if not isinstance(item, dict):
        raise ValueError("Every annotation must be an object.")
    return Annotation(
        anchor=_required_text(item, "anchor"),
        translation=_optional_text(item, "translation") or None,
        role=_required_text(item, "role"),
        context=_required_text(item, "context"),
        explanation=_required_text(item, "explanation"),
        takeaway=_required_text(item, "takeaway"),
        caveat=_required_text(item, "caveat"),
        focus_points=_focus_points_from_payload(item),
    )


def _optional_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Provider response field '{key}' must be a string.")
    return value.strip()


def _focus_points_from_payload(payload: dict[str, Any]) -> tuple[FocusPoint, ...]:
    """Read the optional source-span teaching cards without breaking old clients."""

    raw_points = payload.get("focus_points", [])
    if raw_points is None:
        return ()
    if not isinstance(raw_points, list):
        raise ValueError("Provider response field 'focus_points' must be an array when supplied.")
    points: list[FocusPoint] = []
    for raw_point in raw_points:
        if not isinstance(raw_point, dict):
            raise ValueError("Every focus point must be an object.")
        formula_latex = raw_point.get("formula_latex")
        if formula_latex is not None and not isinstance(formula_latex, str):
            raise ValueError("Focus point field 'formula_latex' must be a string when supplied.")
        points.append(
            FocusPoint(
                quote=_required_text(raw_point, "quote"),
                kind=_required_text(raw_point, "kind"),
                explanation=_required_text(raw_point, "explanation"),
                formula_latex=formula_latex.strip() if isinstance(formula_latex, str) and formula_latex.strip() else None,
            )
        )
    return tuple(points)
