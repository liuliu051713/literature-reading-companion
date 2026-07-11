"""Domain models shared by extractors, providers, quality checks, and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Paragraph:
    anchor: str
    text: str
    section: str | None = None
    page_number: int | None = None


@dataclass(frozen=True)
class SourceDocument:
    source_path: Path
    title: str
    paragraphs: tuple[Paragraph, ...]


@dataclass(frozen=True)
class PaperMap:
    title: str
    research_question: str
    central_claim: str
    argument_map: tuple[str, ...]
    scope_notes: str


@dataclass(frozen=True)
class FocusPoint:
    """A source quotation that deserves a close, reader-facing explanation.

    ``quote`` is deliberately kept as exact source text instead of a character
    offset.  PDF extraction is not stable enough across viewers to promise
    offsets, while an exact quotation can be validated before it is rendered
    and can be highlighted safely in both HTML and DOCX.
    """

    quote: str
    kind: str
    explanation: str
    formula_latex: str | None = None


@dataclass(frozen=True)
class Annotation:
    anchor: str
    role: str
    context: str
    explanation: str
    takeaway: str
    caveat: str
    translation: str | None = None
    focus_points: tuple[FocusPoint, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReadingCopy:
    source: SourceDocument
    paper_map: PaperMap
    annotations: tuple[Annotation, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OutputPaths:
    html: Path | None = None
    docx: Path | None = None
