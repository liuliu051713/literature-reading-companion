"""Interactive, self-contained HTML renderer for source-led deep reading."""

from __future__ import annotations

from html import escape
from pathlib import Path
import re

from ..math_markup import MathChunk, TextChunk, render_html_markup, split_math_markup
from ..models import Annotation, FocusPoint, ReadingCopy


_FOCUS_LABELS = {
    "claim": "核心主张",
    "term": "关键术语",
    "mechanism": "推理机制",
    "evidence": "证据与方法",
    "formula": "公式停读点",
    "limitation": "结论边界",
}


def render_html(reading_copy: ReadingCopy, path: str | Path) -> Path:
    """Render an original-first reading copy with clickable source highlights."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    annotation_by_anchor = {annotation.anchor: annotation for annotation in reading_copy.annotations}
    rows = [
        _render_passage(
            paragraph.anchor,
            paragraph.text,
            paragraph.section,
            paragraph.page_number,
            annotation_by_anchor[paragraph.anchor],
        )
        for paragraph in reading_copy.source.paragraphs
    ]
    paper_map = reading_copy.paper_map
    has_translation = any(annotation.translation for annotation in reading_copy.annotations)
    translation_controls = (
        """
        <button type="button" class="mode-button is-active" data-source-mode="dual" aria-pressed="true">原文 + 中文翻译</button>
        <button type="button" class="mode-button" data-source-mode="original" aria-pressed="false">只看原文</button>
        <button type="button" class="mode-button" data-source-mode="translation" aria-pressed="false">只看中文翻译</button>
        """
        if has_translation
        else """
        <button type="button" class="mode-button is-active" data-source-mode="original" aria-pressed="true">只看原文</button>
        <span class="translation-unavailable">本次未请求全文翻译；左侧始终保留原文。</span>
        """
    )
    html = f"""<!doctype html>
<html lang="zh-CN" data-source-mode="{'dual' if has_translation else 'original'}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(reading_copy.source.title)} — 文献深度阅读版</title>
  <style>
    :root {{ color-scheme: light; --ink:#172033; --muted:#62728a; --line:#dbe3ee; --paper:#fff; --rail:#f6f8fc; --blue:#215ad8; --blue-soft:#e9f0ff; --orange:#ee7d12; --orange-soft:#fff1e1; --green:#087560; --green-soft:#ddf5ef; --purple:#7447c8; --purple-soft:#f0e9ff; --red:#b73752; --red-soft:#ffeaee; --shadow:0 10px 34px rgba(24,39,75,.07); }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; background:#eef2f7; color:var(--ink); font:16px/1.78 "Microsoft YaHei", "Noto Sans CJK SC", Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }}
    main {{ max-width:1540px; margin:30px auto; padding:0 24px 64px; }}
    header, .paper-map, .reading-guide, article {{ background:var(--paper); border:1px solid var(--line); border-radius:15px; box-shadow:var(--shadow); }}
    header {{ padding:30px 34px 26px; }}
    h1 {{ margin:0 0 10px; font-size:clamp(1.8rem,3.2vw,2.65rem); line-height:1.2; letter-spacing:-.025em; }}
    h2 {{ margin:0; font-size:1.16rem; }}
    h3 {{ margin:0; font-size:1.06rem; }}
    .meta, .anchor, .translation-unavailable {{ color:var(--muted); font-size:.86rem; }}
    .paper-map {{ margin-top:18px; padding:24px 32px; }}
    .paper-map dl {{ display:grid; grid-template-columns:155px 1fr; gap:8px 18px; margin:13px 0 0; }}
    .paper-map dt {{ color:var(--muted); font-weight:750; }}
    .paper-map dd {{ margin:0; }}
    .reading-guide {{ display:flex; align-items:center; justify-content:space-between; gap:18px; margin-top:18px; padding:18px 22px; }}
    .guide-copy {{ max-width:780px; }}
    .guide-copy p {{ margin:4px 0 0; color:var(--muted); font-size:.92rem; }}
    .mode-switcher {{ display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }}
    .mode-button {{ appearance:none; border:1px solid #b8c9e5; border-radius:999px; padding:7px 12px; background:#fff; color:#31517c; font:700 .84rem/1 inherit; cursor:pointer; }}
    .mode-button:hover, .mode-button.is-active {{ color:#fff; background:var(--blue); border-color:var(--blue); }}
    .reading-copy {{ display:grid; gap:18px; margin-top:18px; }}
    article {{ display:grid; grid-template-columns:minmax(0,1.08fr) minmax(360px,.92fr); overflow:hidden; scroll-margin-top:20px; }}
    .source, .note {{ min-width:0; padding:25px 29px; }}
    .source {{ border-right:1px solid var(--line); background:#fff; }}
    .note {{ background:var(--rail); }}
    .passage-heading {{ display:flex; align-items:baseline; justify-content:space-between; gap:12px; }}
    .section {{ color:var(--blue); font-size:.8rem; font-weight:800; letter-spacing:.04em; text-transform:uppercase; }}
    .source-help {{ margin:10px 0 14px; color:var(--muted); font-size:.83rem; }}
    .source-text, .translation-content, .explanation, .focus-explanation, .note dd {{ white-space:pre-wrap; }}
    .source-text {{ padding:15px 17px; border:1px solid #e0e7f0; border-radius:11px; background:#fff; font-family:Georgia, "Times New Roman", "Noto Serif", serif; font-size:1.05rem; line-height:1.92; cursor:text; }}
    .source-text:focus-within, .source-text.is-active {{ border-color:#8baaf0; box-shadow:0 0 0 3px rgba(33,90,216,.10); }}
    .source-text::selection {{ background:#bcd1ff; color:inherit; }}
    .source-highlight {{ display:inline; appearance:none; padding:0 .06em; border:0; border-bottom:2px solid currentColor; border-radius:3px; background:transparent; color:inherit; font:inherit; text-align:inherit; cursor:pointer; transition:background .15s ease, box-shadow .15s ease; }}
    .source-highlight:hover, .source-highlight.is-active {{ box-shadow:0 2px 0 currentColor; }}
    .highlight-claim {{ background:var(--blue-soft); color:#173e99; }}
    .highlight-term {{ background:var(--purple-soft); color:#5b259f; }}
    .highlight-mechanism {{ background:var(--green-soft); color:#056451; }}
    .highlight-evidence {{ background:var(--orange-soft); color:#9a4800; }}
    .highlight-formula {{ background:#fff4bd; color:#775c00; }}
    .highlight-limitation {{ background:var(--red-soft); color:#982943; }}
    .translation {{ margin-top:15px; padding:15px 17px; border:1px dashed #a9bad4; border-radius:11px; background:#f8fbff; }}
    .translation-label {{ margin-bottom:6px; color:#385e99; font-size:.79rem; font-weight:800; letter-spacing:.04em; }}
    [data-source-mode="original"] .translation {{ display:none; }}
    [data-source-mode="translation"] .source-original, [data-source-mode="translation"] .source-help {{ display:none; }}
    [data-source-mode="translation"] .translation {{ margin-top:0; }}
    .note-header {{ display:flex; align-items:center; justify-content:space-between; gap:12px; }}
    .deep-read {{ margin-top:13px; padding:17px 18px; border:1px solid #cad8f8; border-left:4px solid var(--blue); border-radius:11px; background:#fff; }}
    .deep-read h3 {{ color:#173f96; }}
    .explanation {{ margin-top:8px; line-height:1.88; }}
    .focus-walkthrough {{ margin-top:15px; }}
    .focus-walkthrough h3 {{ margin-bottom:8px; color:#293d5f; }}
    .focus-card {{ margin:9px 0; border:1px solid #d4deee; border-radius:11px; background:#fff; overflow:hidden; transition:box-shadow .15s ease, border-color .15s ease; }}
    .focus-card.is-active {{ border-color:#5b87e9; box-shadow:0 0 0 3px rgba(33,90,216,.12); }}
    .focus-card summary {{ display:grid; grid-template-columns:auto 1fr; gap:9px; padding:12px 14px; cursor:pointer; list-style:none; }}
    .focus-card summary::-webkit-details-marker {{ display:none; }}
    .focus-card summary::after {{ content:"⌄"; grid-column:2; justify-self:end; grid-row:1; color:#57719a; }}
    .focus-card[open] summary::after {{ content:"⌃"; }}
    .focus-number {{ align-self:start; padding:2px 7px; border-radius:999px; background:var(--blue-soft); color:#173f96; font-size:.76rem; font-weight:800; white-space:nowrap; }}
    .focus-quote {{ grid-column:2; color:#1d273a; font-family:Georgia, "Times New Roman", serif; font-size:.95rem; line-height:1.55; }}
    .focus-body {{ padding:0 14px 15px 48px; }}
    .focus-explanation {{ line-height:1.82; }}
    .formula-lesson {{ margin:11px 0; padding:10px 12px; border-radius:8px; background:#fff9dc; }}
    .formula-label {{ color:#695100; font-size:.78rem; font-weight:800; }}
    .argument-context {{ margin-top:14px; border-top:1px solid #dfe6f0; }}
    .argument-context summary {{ padding:11px 0; color:#365780; font-weight:750; cursor:pointer; }}
    .argument-context dl {{ display:grid; gap:9px; margin:0 0 4px; }}
    .argument-context dl > div {{ padding:10px 12px; border-radius:9px; background:rgba(255,255,255,.66); }}
    .argument-context dt {{ color:#547097; font-size:.77rem; font-weight:800; letter-spacing:.03em; }}
    .argument-context dd {{ margin:3px 0 0; font-size:.93rem; }}
    .ask-more {{ margin-top:14px; padding:12px 13px; border-radius:10px; border:1px dashed #aebfda; background:rgba(255,255,255,.6); }}
    .ask-more strong {{ display:block; color:#263f68; font-size:.91rem; }}
    .ask-more p {{ margin:4px 0 9px; color:var(--muted); font-size:.82rem; line-height:1.55; }}
    .copy-selection {{ appearance:none; border:1px solid #9cb4df; border-radius:7px; padding:6px 9px; background:#fff; color:#234d9d; font:700 .79rem/1.2 inherit; cursor:pointer; }}
    .copy-selection:disabled {{ cursor:not-allowed; opacity:.55; }}
    .selection-status {{ display:block; margin-top:6px; color:#466184; font-size:.78rem; line-height:1.5; }}
    .math-inline {{ display:inline-block; padding:0 .08em; vertical-align:middle; font-family:"Cambria Math", "STIX Two Math", serif; }}
    .math-display {{ display:block; overflow-x:auto; margin:12px 0; padding:10px 12px; border-radius:8px; background:#f7f9fe; text-align:center; font-family:"Cambria Math", "STIX Two Math", serif; }}
    math {{ font-size:1.05em; }}
    .warning {{ margin-top:18px; padding:12px 16px; border-left:4px solid #d59519; border-radius:9px; background:#fff8e8; }}
    @media (max-width:900px) {{ main {{ margin-top:16px; padding:0 12px 36px; }} header, .paper-map, .source, .note {{ padding:20px; }} .reading-guide {{ display:block; }} .mode-switcher {{ margin-top:12px; justify-content:flex-start; }} article {{ grid-template-columns:1fr; }} .source {{ border-right:0; border-bottom:1px solid var(--line); }} .paper-map dl {{ grid-template-columns:1fr; gap:2px; }} .focus-body {{ padding-left:14px; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <div class="meta">文献深度阅读版 · 原始文件仅在本地临时保存</div>
      <h1>{escape(reading_copy.source.title)}</h1>
      <div class="meta">原始文件：{escape(reading_copy.source.source_path.name)}</div>
    </header>
    <section class="paper-map" aria-labelledby="map-title">
      <h2 id="map-title">论文整体阅读地图</h2>
      <dl>
        <dt>研究问题</dt><dd>{render_html_markup(paper_map.research_question)}</dd>
        <dt>核心主张</dt><dd>{render_html_markup(paper_map.central_claim)}</dd>
        <dt>论证主线</dt><dd>{render_html_markup(" → ".join(paper_map.argument_map))}</dd>
        <dt>适用范围与说明</dt><dd>{render_html_markup(paper_map.scope_notes)}</dd>
      </dl>
    </section>
    <section class="reading-guide" aria-label="阅读方式">
      <div class="guide-copy">
        <h2>原文与讲解一一对应</h2>
        <p>左侧保留正文；带底色的文字是值得停下来读的重点。点击它会定位到右侧对应讲解；也可在左侧拖选任意句子，准备一条向 ChatGPT 继续追问的请求。</p>
      </div>
      <div class="mode-switcher" aria-label="原文与翻译显示方式">{translation_controls}</div>
    </section>
    {_warnings(reading_copy.warnings)}
    <section class="reading-copy" aria-label="原文对应深度批注">
      {"".join(rows)}
    </section>
  </main>
  <script>
    (() => {{
      const selectionByAnchor = new Map();
      const modeButtons = [...document.querySelectorAll('[data-source-mode]')];
      modeButtons.forEach((button) => button.addEventListener('click', () => {{
        document.documentElement.dataset.sourceMode = button.dataset.sourceMode;
        modeButtons.forEach((other) => {{
          const active = other === button;
          other.classList.toggle('is-active', active);
          other.setAttribute('aria-pressed', String(active));
        }});
      }}));

      const activatePassage = (anchor, focusId) => {{
        const source = document.querySelector(`.source-text[data-anchor="${{CSS.escape(anchor)}}"]`);
        const note = document.getElementById(`note-${{anchor}}`);
        document.querySelectorAll('.source-text.is-active, .focus-card.is-active, .source-highlight.is-active')
          .forEach((element) => element.classList.remove('is-active'));
        if (source) source.classList.add('is-active');
        if (note) note.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        if (focusId) {{
          const card = document.getElementById(focusId);
          const sourceHighlight = document.querySelector(`[data-focus-target="${{CSS.escape(focusId)}}"]`);
          if (card) {{ card.open = true; card.classList.add('is-active'); }}
          if (sourceHighlight) sourceHighlight.classList.add('is-active');
        }}
      }};

      document.querySelectorAll('.source-highlight').forEach((highlight) => highlight.addEventListener('click', (event) => {{
        event.preventDefault();
        event.stopPropagation();
        activatePassage(highlight.dataset.anchor, highlight.dataset.focusTarget);
      }}));

      document.querySelectorAll('.source-text').forEach((source) => {{
        source.addEventListener('click', () => activatePassage(source.dataset.anchor));
        source.addEventListener('mouseup', () => {{
          const selected = window.getSelection()?.toString().trim() || '';
          if (selected.length < 3 || !source.contains(window.getSelection()?.anchorNode)) return;
          selectionByAnchor.set(source.dataset.anchor, selected);
          activatePassage(source.dataset.anchor);
          const button = document.querySelector(`.copy-selection[data-anchor="${{CSS.escape(source.dataset.anchor)}}"]`);
          const status = document.querySelector(`.selection-status[data-anchor="${{CSS.escape(source.dataset.anchor)}}"]`);
          if (button) button.disabled = false;
          if (status) status.textContent = `已选中：“${{selected.length > 72 ? selected.slice(0, 72) + '…' : selected}}”`;
        }});
      }}));

      document.querySelectorAll('.copy-selection').forEach((button) => button.addEventListener('click', async () => {{
        const selected = selectionByAnchor.get(button.dataset.anchor);
        if (!selected) return;
        const request = `请使用 Literature Reading Companion 深入解释锚点 ${{button.dataset.anchor}} 中这句原文：\n“${{selected}}”\n请结合前后文，用零基础读者能理解的中文说明术语、推理和（如有）公式。`;
        try {{
          await navigator.clipboard.writeText(request);
          button.textContent = '已复制，请粘贴到当前 ChatGPT 对话';
        }} catch (_) {{
          button.textContent = '复制失败，请手动复制选中的原文';
        }}
      }}));
    }})();
  </script>
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
        f'''<section class="translation" aria-label="{escape(anchor)} 的中文翻译">
  <div class="translation-label">中文翻译</div>
  <div class="translation-content">{render_html_markup(annotation.translation)}</div>
</section>'''
        if annotation.translation
        else ""
    )
    return f'''<article id="{escape(anchor)}" data-anchor="{escape(anchor)}">
  <section class="source" aria-label="{escape(anchor)} 原文">
    <div class="passage-heading">
      <div class="section">{escape(section or "原文段落")}</div>
      <div class="anchor">{escape(" · ".join(source_meta))}</div>
    </div>
    <div class="source-help">点击彩色重点可查看对应讲解；拖选任意原文句子可继续追问。</div>
    <div class="source-original source-text" data-anchor="{escape(anchor)}">{_render_source_with_focus(text, annotation.focus_points, anchor)}</div>
    {translation}
  </section>
  <aside class="note" id="note-{escape(anchor)}" aria-label="{escape(anchor)} 的精读批注">
    <div class="note-header"><div class="anchor">中文精读 · {escape(anchor)}</div><div class="anchor">与左侧原文对应</div></div>
    <section class="deep-read" aria-label="{escape(anchor)} 的逐段精读">
      <h3>先读懂这一段在说什么</h3>
      <div class="explanation">{render_html_markup(annotation.explanation)}</div>
    </section>
    {_render_focus_points(annotation, anchor)}
    <details class="argument-context">
      <summary>放回全文来看：论证位置、上下文与边界</summary>
      <dl>
        <div><dt>这一段在全文中做什么</dt><dd>{render_html_markup(annotation.role)}</dd></div>
        <div><dt>它具体承接什么、又为后文准备什么</dt><dd>{render_html_markup(annotation.context)}</dd></div>
        <div><dt>读完应带走的理解</dt><dd>{render_html_markup(annotation.takeaway)}</dd></div>
        <div><dt>证据边界或阅读提醒</dt><dd>{render_html_markup(annotation.caveat)}</dd></div>
      </dl>
    </details>
    <section class="ask-more" aria-label="继续追问 {escape(anchor)}">
      <strong>这段里还有一句没被标出，但你想弄懂？</strong>
      <p>在左侧拖选那句原文，再复制提问到当前 ChatGPT 对话；ChatGPT 会取得该句的前后文后继续讲解。</p>
      <button class="copy-selection" type="button" data-anchor="{escape(anchor)}" disabled>复制所选句子的提问</button>
      <output class="selection-status" data-anchor="{escape(anchor)}">尚未选中原文。</output>
    </section>
  </aside>
</article>'''


def _render_source_with_focus(text: str, points: tuple[FocusPoint, ...], anchor: str) -> str:
    """Highlight verified source quotations without losing MathML rendering."""

    rendered: list[str] = []
    for chunk in split_math_markup(text):
        if isinstance(chunk, TextChunk):
            rendered.append(_render_text_with_focus(chunk.text, points, anchor))
            continue
        rendered.append(_render_math_with_focus(chunk, points, anchor))
    return "".join(rendered)


def _render_text_with_focus(text: str, points: tuple[FocusPoint, ...], anchor: str) -> str:
    matches: list[tuple[int, int, int, FocusPoint]] = []
    for index, point in enumerate(points, start=1):
        start = text.find(point.quote)
        if start >= 0:
            matches.append((start, start + len(point.quote), index, point))
    matches.sort(key=lambda match: (match[0], -(match[1] - match[0])))
    output: list[str] = []
    position = 0
    for start, end, index, point in matches:
        if start < position:
            continue
        output.append(render_html_markup(text[position:start]))
        output.append(_highlight_html(point.quote, point, anchor, index))
        position = end
    output.append(render_html_markup(text[position:]))
    return "".join(output)


def _render_math_with_focus(chunk: MathChunk, points: tuple[FocusPoint, ...], anchor: str) -> str:
    rendered_math = render_html_markup(r"\[" + chunk.latex + r"\]" if chunk.display else r"\(" + chunk.latex + r"\)")
    point_index = next(
        (
            index
            for index, point in enumerate(points, start=1)
            if point.kind == "formula"
            and (_normalise(point.formula_latex or "") == _normalise(chunk.latex) or _normalise(point.quote) in _normalise(chunk.latex))
        ),
        None,
    )
    if point_index is None:
        return rendered_math
    point = points[point_index - 1]
    return _highlight_html(rendered_math, point, anchor, point_index, already_html=True)


def _highlight_html(
    content: str,
    point: FocusPoint,
    anchor: str,
    index: int,
    *,
    already_html: bool = False,
) -> str:
    safe_content = content if already_html else escape(content)
    focus_id = _focus_id(anchor, index)
    kind = point.kind if point.kind in _FOCUS_LABELS else "claim"
    return (
        f'<button type="button" class="source-highlight highlight-{kind}" '
        f'data-anchor="{escape(anchor)}" data-focus-target="{escape(focus_id)}" '
        f'aria-label="查看{escape(_FOCUS_LABELS.get(kind, "重点"))}讲解">{safe_content}</button>'
    )


def _render_focus_points(annotation: Annotation, anchor: str) -> str:
    if not annotation.focus_points:
        return ""
    cards = []
    for index, point in enumerate(annotation.focus_points, start=1):
        kind_label = _FOCUS_LABELS.get(point.kind, "重点")
        formula = ""
        if point.formula_latex:
            formula_markup = render_html_markup("\\[" + point.formula_latex + "\\]")
            formula = (
                '<section class="formula-lesson"><div class="formula-label">把原文公式写清楚</div>'
                f'<div>{formula_markup}</div></section>'
            )
        cards.append(
            f'''<details class="focus-card" id="{escape(_focus_id(anchor, index))}">
  <summary><span class="focus-number">重点 {index} · {escape(kind_label)}</span><span class="focus-quote">{escape(point.quote)}</span></summary>
  <div class="focus-body">{formula}<div class="focus-explanation">{render_html_markup(point.explanation)}</div></div>
</details>'''
        )
    return '<section class="focus-walkthrough" aria-label="原文重点逐点讲解"><h3>停下来读：左侧重点逐句讲解</h3>' + "".join(cards) + "</section>"


def _focus_id(anchor: str, index: int) -> str:
    return f"focus-{anchor}-{index}"


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _warnings(warnings: tuple[str, ...]) -> str:
    if not warnings:
        return ""
    content = "".join(f"<div>{render_html_markup(warning)}</div>" for warning in warnings)
    return f'<section class="warning" aria-label="提示">{content}</section>'
