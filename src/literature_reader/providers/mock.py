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
            research_question="离线 mock 模式不会推断论文的研究问题。",
            central_claim="离线 mock 模式不会推断作者的核心主张。",
            argument_map=(
                "该阅读地图只用于验证本地提取、锚点对应和排版流程。",
                "请配置 OpenAI 或 Gemini，以生成具有实际阅读价值的内容。",
            ),
            scope_notes="mock 模式不生成语义解释，也不会把文档文字发送给外部服务。",
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
                neighbours.append(f"前一段为 {local_previous.anchor}")
            if local_following:
                neighbours.append(f"后一段为 {local_following.anchor}")
            context = (
                "该来源对应的占位批注：" + "；".join(neighbours) + "。"
                if neighbours
                else "该来源对应的占位批注没有可用的相邻段落。"
            )
            translation = (
                "[mock 模式：未生成真实中文翻译。请配置 AI 模型后重新运行。]"
                if config.translation == "full"
                else None
            )
            annotations.append(
                Annotation(
                    anchor=paragraph.anchor,
                    translation=translation,
                    role="流程验证占位批注",
                    context=context,
                    explanation=(
                        "mock 模式用于确认该原文段落可以被提取、编号、核对并排版；"
                        "它不声称解释了作者的真实含义。"
                    ),
                    takeaway="如需真正帮助理解论文，请配置 OpenAI 或 Gemini 后重新生成。",
                    caveat="离线 mock 模式不生成任何实质性的学术解释。",
                )
            )
        return tuple(annotations)
