from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from literature_reader.config import RunConfig
from literature_reader.pipeline import annotate_document, write_outputs


class PipelineTests(unittest.TestCase):
    def test_mock_pipeline_writes_aligned_html_and_docx(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "paper.txt"
            source.write_text(
                "A Fictional Paper\n\n"
                "1 Introduction\n\n"
                "The first passage explains the problem.\n\n"
                "The second passage explains why the problem matters.",
                encoding="utf-8",
            )
            reading_copy = annotate_document(source, RunConfig(provider="mock", batch_size=1))
            paths = write_outputs(reading_copy, root / "output", "all")

            self.assertEqual(
                [annotation.anchor for annotation in reading_copy.annotations],
                ["P001", "P002"],
            )
            self.assertIn("后一段为 P002", reading_copy.annotations[0].context)
            self.assertIn("前一段为 P001", reading_copy.annotations[1].context)
            self.assertTrue(paths.html and paths.html.exists())
            self.assertTrue(paths.docx and paths.docx.exists())
            html = paths.html.read_text(encoding="utf-8")
            self.assertIn('id="P001"', html)
            self.assertIn("中文精读 · P002", html)
            self.assertIn("流程验证占位批注", html)
            self.assertIn("source-highlight", html)
            self.assertIn("The first passage explains the problem.", html)

    def test_mock_translation_mode_fills_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "paper.txt"
            source.write_text("Title\n\nA body paragraph with enough words.", encoding="utf-8")
            reading_copy = annotate_document(source, RunConfig(provider="mock", translation="full"))

        self.assertTrue(reading_copy.annotations[0].translation)


if __name__ == "__main__":
    unittest.main()
