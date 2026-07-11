from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from literature_reader.chatgpt_app_service import ReadingJobError, ReadingJobStore


DETAILED_EXPLANATION = (
    "作者不是只提出一个阅读辅助工具，而是在说明为什么段落级批注需要和全文论证一起理解。"
    "换句话说，读者要先知道这里解决的具体问题，再看它如何为下一段的贡献说明铺路。"
    "这种解释把局部句子放回论文的推理链中，因此即使不熟悉研究领域，也能判断作者的结论依赖哪些前提。"
)

FOCUS_POINTS = [
    {
        "quote": "The first paragraph sets up the research problem.",
        "kind": "claim",
        "explanation": (
            "这句不是泛泛地说文章有一个问题，而是明确告诉读者后续所有方法和贡献都要回应这个研究缺口。"
            "把它标出来，读者就能在后文判断作者提出的方案是否真的解决了这个问题，而不是只增加了一个新术语。"
        ),
    }
]


class ChatGPTAppServiceTests(unittest.TestCase):
    def test_store_keeps_source_notes_aligned_and_renders_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ReadingJobStore(Path(directory), batch_size=1)
            started = store.create_from_bytes(
                filename="paper.txt",
                content=(
                    b"A Paper About Reading\n\n"
                    b"1 Introduction\n\n"
                    b"The first paragraph sets up the research problem.\n\n"
                    b"The second paragraph explains the proposed contribution."
                ),
                translation="none",
            )
            job_id = started["job_id"]

            outline = store.document_outline(job_id)
            self.assertEqual(outline["paragraph_count"], 2)
            store.save_paper_map(
                job_id,
                research_question="如何帮助读者把握论文的研究问题？",
                central_claim="对应批注能把局部段落和全文论证联系起来。",
                argument_map=["提出问题", "说明贡献"],
                scope_notes="这是一个用于验证工作流的示例。",
            )

            for batch_index in range(started["batch_count"]):
                batch = store.annotation_batch(job_id, batch_index)
                self.assertIn("paper_map", batch)
                self.assertIn("surrounding_context", batch)
                self.assertIn("零基础", batch["instruction"])
                store.save_annotations(
                    job_id,
                    [
                        {
                            "anchor": paragraph["anchor"],
                            "role": "论证中的关键步骤",
                            "context": "承接前文并为后文的主张提供基础。",
                            "explanation": DETAILED_EXPLANATION,
                            "takeaway": "不要只看一句话，要看它服务于什么论证目标。",
                            "caveat": "这是示例文本，不应外推为真实实证结论。",
                            "focus_points": [
                                {
                                    **FOCUS_POINTS[0],
                                    "quote": paragraph["text"],
                                }
                            ],
                        }
                        for paragraph in batch["paragraphs"]
                    ],
                )

            progress = store.progress(job_id)
            self.assertTrue(progress["complete"])
            paths = store.render(job_id, "all")
            self.assertTrue(paths["html"].exists())
            self.assertTrue(paths["docx"].exists())
            html = paths["html"].read_text(encoding="utf-8")
            self.assertIn("原文与讲解一一对应", html)
            self.assertIn('id="P001"', html)
            self.assertIn("逐段精读", html)
            self.assertIn("source-highlight", html)

    def test_store_rejects_short_page_summary_in_deep_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ReadingJobStore(Path(directory), batch_size=1)
            started = store.create_from_bytes(
                filename="paper.txt",
                content=b"Title\n\nA short paragraph.",
                translation="none",
            )
            with self.assertRaisesRegex(ReadingJobError, "too short for deep reading"):
                store.save_annotations(
                    started["job_id"],
                    [
                        {
                            "anchor": "P001",
                            "role": "提出问题。",
                            "context": "承接前文并引出后文。",
                            "explanation": "本段作用：提出研究问题。",
                            "takeaway": "了解问题。",
                            "caveat": "这是示例。",
                            "focus_points": [],
                        }
                    ],
                )

    def test_full_translation_requires_translation_for_every_annotation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ReadingJobStore(Path(directory), batch_size=4)
            started = store.create_from_bytes(
                filename="paper.txt",
                content=b"Title\n\nA paragraph that needs a translated reading copy.",
                translation="full",
            )
            job_id = started["job_id"]
            with self.assertRaises(ReadingJobError):
                store.save_annotations(
                    job_id,
                    [
                        {
                            "anchor": "P001",
                            "role": "作用",
                            "context": "上下文",
                            "explanation": "解释",
                            "takeaway": "要点",
                            "caveat": "提醒",
                            "focus_points": [
                                {
                                    "quote": "A paragraph that needs a translated reading copy.",
                                    "kind": "claim",
                                    "explanation": "这句话只是测试材料的正文，因此它的用途是验证翻译模式会要求每个原文段落都有对应字段。"
                                    "它没有提供真实研究结论，读者不应把这一句当作可外推的学术发现。",
                                }
                            ],
                        }
                    ],
                )

    def test_selected_sentence_returns_its_own_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ReadingJobStore(Path(directory), batch_size=2)
            started = store.create_from_bytes(
                filename="paper.txt",
                content=(
                    b"Title\n\n"
                    b"The model assigns a score to every case.\n\n"
                    b"The score determines which case receives review."
                ),
                translation="none",
            )
            result = store.selected_passage_context(
                started["job_id"],
                "P001",
                "assigns a score",
            )

        self.assertEqual(result["anchor"], "P001")
        self.assertEqual(result["following_context"]["anchor"], "P002")
        self.assertIn("不要只总结整段", result["instruction"])


if __name__ == "__main__":
    unittest.main()
