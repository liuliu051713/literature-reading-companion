"""Prompts that make the annotation contract explicit and reviewable."""

from __future__ import annotations

from .config import RunConfig
from .models import PaperMap, Paragraph, SourceDocument


PAPER_MAP_SYSTEM_PROMPT = (
    "You are an academic reading assistant. Build a conservative paper-level map from the "
    "supplied text. Distinguish author claims from your own reading aid. Do not invent "
    "methods, results, citations, or limitations that are absent from the source. "
    "Return only JSON matching the requested schema. Write every textual response field "
    "in Simplified Chinese, except for source anchors and quoted source-language terms."
)

ANNOTATION_SYSTEM_PROMPT = (
    "You are creating source-linked annotations for an academic paper. The purpose is to "
    "help a reader who is new to the field understand the actual passage, not to label the "
    "function of a page. For every requested anchor, write a compact navigation note in "
    "role and context, but make explanation the main teaching text: use 2–4 connected "
    "Simplified-Chinese sentences (normally at least 100 non-whitespace characters) to "
    "state what the author is saying, unpack the causal or logical steps, define unfamiliar "
    "terms in plain language, and explain why the point matters for the next claim. Do not "
    "write an outline such as 'this paragraph introduces…' in explanation. Explain the "
    "substance instead. Context must name the concrete idea inherited from the supplied "
    "previous passage and the question, method, result, or claim prepared for the following "
    "passage; do not use empty phrases such as 'it connects the previous and next text'. "
    "If the source contains a formula, reproduce the key formula or notation in explanation "
    "using \\( ... \\) for inline math or \\[ ... \\] for a displayed formula, for example "
    "\\(R_{i,t}=\\Delta^{ad}_{i,t}C_i\\), then explain each symbol and what changes when a "
    "term increases. Use only source-supported meaning. State uncertainty or missing "
    "evidence in caveat rather than inventing it, and distinguish author claims from your "
    "reader-facing explanation. Return only JSON matching the requested schema. Write role, "
    "context, explanation, takeaway, caveat, and any other reader-facing description in "
    "Simplified Chinese. Preserve source anchors exactly. When translation is requested, "
    "write a faithful Simplified Chinese translation."
)


def build_paper_map_prompt(document: SourceDocument) -> str:
    excerpt = "\n\n".join(f"[{p.anchor}] {p.text}" for p in document.paragraphs)
    return (
        "Create a reading map for this paper.\n\n"
        f"Source title: {document.title}\n"
        f"Paragraphs:\n{excerpt}\n"
    )


def build_annotation_prompt(
    paper_map: PaperMap,
    paragraphs: tuple[Paragraph, ...],
    config: RunConfig,
    previous: Paragraph | None,
    following: Paragraph | None,
) -> str:
    translation_instruction = (
        "Provide a faithful Chinese translation for every source passage in the 'translation' field."
        if config.translation == "full"
        else "Set every 'translation' field to an empty string."
    )
    current_blocks = []
    for index, paragraph in enumerate(paragraphs):
        local_previous = paragraphs[index - 1] if index else previous
        local_following = paragraphs[index + 1] if index + 1 < len(paragraphs) else following
        context_lines = []
        if local_previous:
            context_lines.append(f"Immediate previous [{local_previous.anchor}]: {local_previous.text}")
        if local_following:
            context_lines.append(f"Immediate following [{local_following.anchor}]: {local_following.text}")
        local_context = "\n".join(context_lines) or "No adjacent passage was supplied."
        current_blocks.append(
            (
                f"[{paragraph.anchor}] section={paragraph.section or 'unlabelled'} "
                f"page={paragraph.page_number or 'unknown'}\n{paragraph.text}\n"
                f"Local context for {paragraph.anchor}:\n{local_context}"
            )
        )
    current = "\n\n".join(current_blocks)
    return (
        "The output is a deep-reading companion, not page summaries.\n"
        "For each anchor, use this field contract:\n"
        "- role: one concise sentence about where this passage sits in the argument.\n"
        "- context: identify the specific prior idea it uses and the specific next question or claim it enables.\n"
        "- explanation: 2–4 connected Simplified-Chinese sentences, normally at least 100 non-whitespace "
        "characters. Explain the actual content for a beginner: what the author means, how the reasoning works, "
        "and why it matters. Do not make explanation a list of 'role / connection / key point'.\n"
        "- takeaway: one plain-language conclusion the reader can carry forward.\n"
        "- caveat: only a source-grounded boundary, uncertainty, or an explicit statement that no extra caveat is needed.\n"
        "When a formula or notation appears, use \\( ... \\) for inline math or \\[ ... \\] for displayed math; "
        "write the key notation faithfully and explain its symbols in prose.\n\n"
        "Paper map:\n"
        f"Title: {paper_map.title}\n"
        f"Research question: {paper_map.research_question}\n"
        f"Central claim: {paper_map.central_claim}\n"
        f"Argument map: {' | '.join(paper_map.argument_map)}\n"
        f"Scope notes: {paper_map.scope_notes}\n\n"
        f"Reader focus: {', '.join(config.focus)}\n"
        f"Annotation depth: {config.annotation_depth}\n"
        f"{translation_instruction}\n\n"
        f"Passages requiring one annotation each:\n{current}\n"
    )
