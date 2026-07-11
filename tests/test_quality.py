from __future__ import annotations

import unittest
from pathlib import Path

from literature_reader.config import RunConfig
from literature_reader.models import Annotation, FocusPoint, PaperMap, Paragraph, ReadingCopy, SourceDocument
from literature_reader.quality import AnnotationQualityError, validate_reading_copy


class QualityTests(unittest.TestCase):
    def test_rejects_missing_and_unknown_anchor(self) -> None:
        source = SourceDocument(
            source_path=Path("paper.txt"),
            title="Paper",
            paragraphs=(Paragraph(anchor="P001", text="Source"),),
        )
        reading_copy = ReadingCopy(
            source=source,
            paper_map=PaperMap("Paper", "Question", "Claim", ("Step",), "Scope"),
            annotations=(
                Annotation(
                    anchor="P999",
                    role="Role",
                    context="Context",
                    explanation="Explanation",
                    takeaway="Takeaway",
                    caveat="Caveat",
                ),
            ),
        )
        with self.assertRaises(AnnotationQualityError):
            validate_reading_copy(reading_copy, RunConfig(provider="mock"))

    def test_rejects_focus_quote_that_is_not_in_its_source_paragraph(self) -> None:
        source = SourceDocument(
            source_path=Path("paper.txt"),
            title="Paper",
            paragraphs=(Paragraph(anchor="P001", text="The author defines the score."),),
        )
        reading_copy = ReadingCopy(
            source=source,
            paper_map=PaperMap("Paper", "问题", "主张", ("定义",), "范围"),
            annotations=(
                Annotation(
                    anchor="P001",
                    role="定义关键概念。",
                    context="这是全文唯一段落，因此没有前后段，但它给出后续讨论所需的基础定义。",
                    explanation=(
                        "作者在这里要读者先接受一个可操作的评分定义，而不是直接宣称评分一定正确。"
                        "有了这个定义，读者才能追问分数究竟由什么组成、是否能被观察，以及它会怎样影响后续判断。"
                        "这使抽象概念变成可以被讨论和检验的对象。"
                    ),
                    takeaway="先确认概念如何被定义，再判断后续结论是否可信。",
                    caveat="该示例没有提供真实实证证据，不能外推为方法有效性结论。",
                    focus_points=(
                        FocusPoint(
                            quote="A quote from a different paragraph.",
                            kind="claim",
                            explanation=(
                                "这是一条故意错误的引用，用来验证系统不会把一段看似合理的讲解贴到不存在的原文上。"
                                "只有引用确实来自同一锚点，读者点击高亮时才能相信左右两栏没有发生错位。"
                            ),
                        ),
                    ),
                ),
            ),
        )

        with self.assertRaisesRegex(AnnotationQualityError, "focus-point quote"):
            validate_reading_copy(reading_copy, RunConfig(provider="mock"))


if __name__ == "__main__":
    unittest.main()
