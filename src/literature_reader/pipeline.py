"""End-to-end local reading-copy pipeline."""

from __future__ import annotations

from pathlib import Path

from .config import RunConfig
from .extractors import extract_document
from .models import OutputPaths, ReadingCopy
from .providers import create_provider
from .quality import validate_reading_copy
from .renderers import render_docx, render_html


def annotate_document(input_path: str | Path, config: RunConfig) -> ReadingCopy:
    """Extract, interpret, anchor-check, and return a reading copy."""

    config.validate()
    source = extract_document(input_path)
    provider = create_provider(config)
    paper_map = provider.build_paper_map(source)

    annotations = []
    paragraphs = source.paragraphs
    for start in range(0, len(paragraphs), config.batch_size):
        batch = paragraphs[start : start + config.batch_size]
        previous = paragraphs[start - 1] if start else None
        following_index = start + len(batch)
        following = paragraphs[following_index] if following_index < len(paragraphs) else None
        annotations.extend(provider.annotate(paper_map, batch, config, previous, following))

    provisional_copy = ReadingCopy(source=source, paper_map=paper_map, annotations=tuple(annotations))
    validate_reading_copy(provisional_copy, config)
    annotation_by_anchor = {annotation.anchor: annotation for annotation in annotations}
    ordered_annotations = tuple(annotation_by_anchor[paragraph.anchor] for paragraph in paragraphs)
    reading_copy = ReadingCopy(source=source, paper_map=paper_map, annotations=ordered_annotations)
    warnings = validate_reading_copy(reading_copy, config)
    return ReadingCopy(
        source=reading_copy.source,
        paper_map=reading_copy.paper_map,
        annotations=reading_copy.annotations,
        warnings=warnings,
    )


def write_outputs(reading_copy: ReadingCopy, output_dir: str | Path, output_format: str) -> OutputPaths:
    """Render one or both supported reading-copy formats."""

    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    stem = reading_copy.source.source_path.stem
    html_path = destination / f"{stem}.reading.html"
    docx_path = destination / f"{stem}.reading.docx"

    if output_format == "html":
        render_html(reading_copy, html_path)
        return OutputPaths(html=html_path)
    if output_format == "docx":
        render_docx(reading_copy, docx_path)
        return OutputPaths(docx=docx_path)
    if output_format == "all":
        render_html(reading_copy, html_path)
        render_docx(reading_copy, docx_path)
        return OutputPaths(html=html_path, docx=docx_path)
    raise ValueError(f"Unsupported output format: {output_format}")
