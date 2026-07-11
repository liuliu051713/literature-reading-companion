from __future__ import annotations

import unittest
from pathlib import Path

from literature_reader.config import RunConfig
from literature_reader.models import Annotation, PaperMap, Paragraph, ReadingCopy, SourceDocument
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


if __name__ == "__main__":
    unittest.main()
