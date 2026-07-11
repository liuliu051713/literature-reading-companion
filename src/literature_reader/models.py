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
class Annotation:
    anchor: str
    role: str
    context: str
    explanation: str
    takeaway: str
    caveat: str
    translation: str | None = None


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
