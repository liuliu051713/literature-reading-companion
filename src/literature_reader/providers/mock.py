"""Offline provider used only for pipeline checks and demonstrations."""

from __future__ import annotations

from ..config import RunConfig
from ..models import Annotation, PaperMap, Paragraph, SourceDocument
from .base import ModelProvider


class MockProvider(ModelProvider):
    """Creates visibly synthetic notes without pretending to understand a paper."""

    def build_paper_map(self, document: SourceDocument) -> PaperMap:
        return PaperMap(
            title=document.title,
            research_question="Offline mock mode does not infer a research question.",
            central_claim="Offline mock mode does not infer an author claim.",
            argument_map=(
                "This map exists only to verify the local extraction, alignment, and rendering pipeline.",
                "Choose OpenAI or Gemini to generate substantive reading assistance.",
            ),
            scope_notes="Mock mode produces no semantic interpretation and sends no document text to an external service.",
        )

    def annotate(
        self,
        paper_map: PaperMap,
        paragraphs: tuple[Paragraph, ...],
        config: RunConfig,
        previous: Paragraph | None,
        following: Paragraph | None,
    ) -> tuple[Annotation, ...]:
        annotations: list[Annotation] = []
        for index, paragraph in enumerate(paragraphs):
            local_previous = paragraphs[index - 1] if index else previous
            local_following = paragraphs[index + 1] if index + 1 < len(paragraphs) else following
            neighbours = []
            if local_previous:
                neighbours.append(f"preceded by {local_previous.anchor}")
            if local_following:
                neighbours.append(f"followed by {local_following.anchor}")
            context = (
                "This source-linked placeholder is " + " and ".join(neighbours) + "."
                if neighbours
                else "This source-linked placeholder has no supplied neighbouring passage."
            )
            translation = (
                "[Mock mode: no translation generated. Configure an AI provider for a faithful Chinese translation.]"
                if config.translation == "full"
                else None
            )
            annotations.append(
                Annotation(
                    anchor=paragraph.anchor,
                    translation=translation,
                    role="Pipeline validation placeholder",
                    context=context,
                    explanation=(
                        "Mock mode confirms that this source passage can be extracted, anchored, "
                        "checked, and rendered. It does not claim to explain the author's meaning."
                    ),
                    takeaway="Replace mock mode with a configured provider for substantive annotations.",
                    caveat="No semantic interpretation is generated in offline mock mode.",
                )
            )
        return tuple(annotations)
