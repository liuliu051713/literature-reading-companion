"""Self-contained HTML renderer with a source and annotation rail."""

from __future__ import annotations

from html import escape
from pathlib import Path

from ..models import Annotation, ReadingCopy


def render_html(reading_copy: ReadingCopy, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    annotation_by_anchor = {annotation.anchor: annotation for annotation in reading_copy.annotations}
    rows = []
    for paragraph in reading_copy.source.paragraphs:
        annotation = annotation_by_anchor[paragraph.anchor]
        rows.append(_render_passage(paragraph.anchor, paragraph.text, paragraph.section, paragraph.page_number, annotation))

    paper_map = reading_copy.paper_map
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(reading_copy.source.title)} — reading copy</title>
  <style>
    :root {{ color-scheme: light; --ink:#1d2433; --muted:#617086; --line:#dce3eb; --paper:#fff; --note:#f5f8ff; --accent:#2457d6; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background:#eef2f7; color:var(--ink); font:16px/1.68 Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }}
    main {{ max-width:1440px; margin:32px auto; padding:0 24px 56px; }}
    header, .paper-map, article {{ background:var(--paper); border:1px solid var(--line); border-radius:14px; box-shadow:0 8px 28px rgba(24,39,75,.05); }}
    header {{ padding:28px 32px; }}
    h1 {{ margin:0 0 8px; font-size:clamp(1.75rem, 3vw, 2.6rem); line-height:1.2; }}
    h2 {{ margin:0 0 12px; font-size:1.1rem; }}
    .meta, .anchor {{ color:var(--muted); font-size:.85rem; }}
    .paper-map {{ margin-top:18px; padding:24px 32px; }}
    .paper-map dl {{ display:grid; grid-template-columns:160px 1fr; gap:8px 18px; margin:0; }}
    .paper-map dt {{ color:var(--muted); font-weight:650; }}
    .paper-map dd {{ margin:0; }}
    .reading-copy {{ display:grid; gap:18px; margin-top:18px; }}
    article {{ display:grid; grid-template-columns:minmax(0,1.18fr) minmax(320px,.82fr); overflow:hidden; }}
    .source, .note {{ padding:24px 28px; }}
    .source {{ border-right:1px solid var(--line); }}
    .note {{ background:var(--note); }}
    .section {{ color:var(--accent); font-size:.82rem; font-weight:700; letter-spacing:.02em; text-transform:uppercase; }}
    p {{ margin:10px 0 0; white-space:pre-wrap; }}
    .note dl {{ display:grid; gap:12px; margin:0; }}
    .note dt {{ color:var(--accent); font-size:.76rem; font-weight:750; letter-spacing:.07em; text-transform:uppercase; }}
    .note dd {{ margin:2px 0 0; }}
    .translation {{ margin-top:16px; padding-top:14px; border-top:1px dashed #bac8df; }}
    .warning {{ margin-top:16px; padding:12px 16px; border-left:4px solid #d59519; background:#fff8e8; }}
    @media (max-width:850px) {{ main {{ margin-top:16px; padding:0 12px 32px; }} article {{ grid-template-columns:1fr; }} .source {{ border-right:0; border-bottom:1px solid var(--line); }} header, .paper-map, .source, .note {{ padding:20px; }} .paper-map dl {{ grid-template-columns:1fr; gap:2px; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="meta">Annotated reading copy · source preserved locally</div>
      <h1>{escape(reading_copy.source.title)}</h1>
      <div class="meta">Original file: {escape(reading_copy.source.source_path.name)}</div>
    </header>
    <section class="paper-map" aria-labelledby="map-title">
      <h2 id="map-title">Paper-level reading map</h2>
      <dl>
        <dt>Research question</dt><dd>{escape(paper_map.research_question)}</dd>
        <dt>Central claim</dt><dd>{escape(paper_map.central_claim)}</dd>
        <dt>Argument map</dt><dd>{escape(" → ".join(paper_map.argument_map))}</dd>
        <dt>Scope note</dt><dd>{escape(paper_map.scope_notes)}</dd>
      </dl>
    </section>
    {_warnings(reading_copy.warnings)}
    <section class="reading-copy" aria-label="Source-linked annotations">
      {"".join(rows)}
    </section>
  </main>
</body>
</html>
"""
    destination.write_text(html, encoding="utf-8")
    return destination


def _render_passage(
    anchor: str,
    text: str,
    section: str | None,
    page_number: int | None,
    annotation: Annotation,
) -> str:
    source_meta = [anchor]
    if section:
        source_meta.append(section)
    if page_number:
        source_meta.append(f"page {page_number}")
    translation = (
        f'<div class="translation"><div class="anchor">Chinese translation</div><p>{escape(annotation.translation)}</p></div>'
        if annotation.translation
        else ""
    )
    return f"""<article id="{escape(anchor)}">
  <section class="source">
    <div class="section">{escape(section or "Source passage")}</div>
    <div class="anchor">{escape(" · ".join(source_meta))}</div>
    <p>{escape(text)}</p>
    {translation}
  </section>
  <aside class="note" aria-label="Annotation for {escape(anchor)}">
    <div class="anchor">Annotation · {escape(anchor)}</div>
    <dl>
      <div><dt>Role in the paper</dt><dd>{escape(annotation.role)}</dd></div>
      <div><dt>Context</dt><dd>{escape(annotation.context)}</dd></div>
      <div><dt>Reading explanation</dt><dd>{escape(annotation.explanation)}</dd></div>
      <div><dt>Takeaway</dt><dd>{escape(annotation.takeaway)}</dd></div>
      <div><dt>Caveat</dt><dd>{escape(annotation.caveat)}</dd></div>
    </dl>
  </aside>
</article>"""


def _warnings(warnings: tuple[str, ...]) -> str:
    if not warnings:
        return ""
    content = "".join(f"<div>{escape(warning)}</div>" for warning in warnings)
    return f'<section class="warning" aria-label="Warnings">{content}</section>'
