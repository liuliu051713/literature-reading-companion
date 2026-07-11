"""DOCX renderer with source-linked Chinese deep-reading notes.

The document intentionally keeps every note in the same table row as its
source anchor.  Within the note column, the substantive explanation is shown
before the shorter navigation fields so the result reads like a companion, not
like a page-by-page outline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

from ..math_markup import append_docx_markup
from ..models import Annotation, ReadingCopy


_BODY_FONT = "Aptos"
_CJK_FONT = "Microsoft YaHei"


def render_docx(reading_copy: ReadingCopy, path: str | Path) -> Path:
    """Write a two-column DOCX with editable Office Math where markup exists."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    document.core_properties.title = f"{reading_copy.source.title} — 带批注的阅读版"
    _configure_document_fonts(document)

    document.add_heading(reading_copy.source.title, level=0)
    document.add_paragraph(f"带批注的阅读版 · 原始文件：{reading_copy.source.source_path.name}")
    document.add_heading("论文整体阅读地图", level=1)
    _add_labeled_paragraph(document, "研究问题", reading_copy.paper_map.research_question)
    _add_labeled_paragraph(document, "核心主张", reading_copy.paper_map.central_claim)
    _add_labeled_paragraph(document, "论证主线", " → ".join(reading_copy.paper_map.argument_map))
    _add_labeled_paragraph(document, "适用范围与说明", reading_copy.paper_map.scope_notes)

    document.add_heading("原文对应阅读批注", level=1)
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.autofit = True
    _write_table_header(table.rows[0].cells[0], "原文")
    _write_table_header(table.rows[0].cells[1], "中文精读批注")
    annotation_by_anchor = {annotation.anchor: annotation for annotation in reading_copy.annotations}

    for paragraph in reading_copy.source.paragraphs:
        row = table.add_row()
        source_cell, note_cell = row.cells
        source_cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
        note_cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
        _write_source_cell(
            source_cell,
            paragraph.anchor,
            paragraph.text,
            paragraph.section,
            paragraph.page_number,
            annotation_by_anchor[paragraph.anchor],
        )
        _write_note_cell(note_cell, annotation_by_anchor[paragraph.anchor])

    if reading_copy.warnings:
        document.add_heading("提示", level=1)
        for warning in reading_copy.warnings:
            paragraph = document.add_paragraph(style="List Bullet")
            append_docx_markup(paragraph, warning)

    document.save(str(destination))
    return destination


def _configure_document_fonts(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.font.name = _BODY_FONT
    normal.font.size = Pt(10.5)
    _set_east_asia_font(normal, _CJK_FONT)
    for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        style = document.styles[style_name]
        _set_east_asia_font(style, _CJK_FONT)


def _set_east_asia_font(style: Any, font_name: str) -> None:
    properties = style.element.get_or_add_rPr()
    fonts = properties.rFonts
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        properties.insert(0, fonts)
    fonts.set(qn("w:eastAsia"), font_name)


def _write_table_header(cell: Any, text: str) -> None:
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(text)
    run.bold = True
    _set_run_font(run, size=10.5)


def _add_labeled_paragraph(document: Document, label: str, value: str) -> None:
    paragraph = document.add_paragraph()
    label_run = paragraph.add_run(f"{label}: ")
    label_run.bold = True
    _set_run_font(label_run)
    append_docx_markup(paragraph, value)


def _write_source_cell(
    cell: Any,
    anchor: str,
    text: str,
    section: str | None,
    page_number: int | None,
    annotation: Annotation,
) -> None:
    paragraph = cell.paragraphs[0]
    anchor_run = paragraph.add_run(f"[{anchor}] ")
    anchor_run.bold = True
    _set_run_font(anchor_run)
    if section:
        section_run = paragraph.add_run(f"{section} · ")
        section_run.italic = True
        _set_run_font(section_run)
    if page_number:
        page_run = paragraph.add_run(f"page {page_number}")
        _set_run_font(page_run)

    source = cell.add_paragraph()
    append_docx_markup(source, text)
    if annotation.translation:
        translation = cell.add_paragraph()
        translation_label = translation.add_run("中文翻译：")
        translation_label.bold = True
        _set_run_font(translation_label)
        append_docx_markup(translation, annotation.translation)


def _write_note_cell(cell: Any, annotation: Annotation) -> None:
    header = cell.paragraphs[0]
    header_run = header.add_run(f"[{annotation.anchor}] 中文精读")
    header_run.bold = True
    _set_run_font(header_run)

    _write_note_paragraph(cell, "逐段精读", annotation.explanation, lead=True)
    _write_note_paragraph(cell, "这段放在全文中的位置", annotation.role)
    _write_note_paragraph(cell, "它怎样接上前后文", annotation.context)
    _write_note_paragraph(cell, "读完应真正理解什么", annotation.takeaway)
    _write_note_paragraph(cell, "阅读边界", annotation.caveat)


def _write_note_paragraph(cell: Any, label: str, value: str, *, lead: bool = False) -> None:
    paragraph = cell.add_paragraph()
    label_run = paragraph.add_run(f"{label}：")
    label_run.bold = True
    _set_run_font(label_run, size=10.5 if lead else 9.5)
    if lead:
        paragraph.paragraph_format.space_before = Pt(5)
        paragraph.paragraph_format.space_after = Pt(6)
    append_docx_markup(paragraph, value)


def _set_run_font(run: Any, *, size: float | None = None) -> None:
    run.font.name = _BODY_FONT
    if size is not None:
        run.font.size = Pt(size)
    properties = run._element.get_or_add_rPr()
    fonts = properties.rFonts
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        properties.insert(0, fonts)
    fonts.set(qn("w:eastAsia"), _CJK_FONT)
