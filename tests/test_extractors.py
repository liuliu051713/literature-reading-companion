from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from literature_reader.extractors import extract_document


class ExtractorTests(unittest.TestCase):
    def test_txt_extraction_preserves_title_and_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "paper.txt"
            source.write_text(
                "A Fictional Paper Title\n\n"
                "1 Introduction\n\n"
                "This is the first body paragraph.\n\n"
                "This is the second body paragraph.",
                encoding="utf-8",
            )
            document = extract_document(source)

        self.assertEqual(document.title, "A Fictional Paper Title")
        self.assertEqual([paragraph.anchor for paragraph in document.paragraphs], ["P001", "P002"])
        self.assertEqual(document.paragraphs[0].section, "1 Introduction")

    def test_rejects_unknown_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "paper.md"
            source.write_text("content", encoding="utf-8")
            with self.assertRaises(ValueError):
                extract_document(source)


if __name__ == "__main__":
    unittest.main()
