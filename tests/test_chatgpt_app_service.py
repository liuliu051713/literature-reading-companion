from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from literature_reader.chatgpt_app_service import ReadingJobError, ReadingJobStore


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
                store.save_annotations(
                    job_id,
                    [
                        {
                            "anchor": paragraph["anchor"],
                            "role": "论证中的关键步骤",
                            "context": "承接前文并为后文的主张提供基础。",
                            "explanation": "它说明作者为什么要提出这个阅读辅助方案。",
                            "takeaway": "不要只看一句话，要看它服务于什么论证目标。",
                            "caveat": "这是示例文本，不应外推为真实实证结论。",
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
            self.assertIn("对应批注", html)
            self.assertIn('id="P001"', html)

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
                        }
                    ],
                )


if __name__ == "__main__":
    unittest.main()
