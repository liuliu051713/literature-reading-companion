from __future__ import annotations

import json
import unittest
from pathlib import Path

from literature_reader.schema import annotation_response_schema


class SchemaTests(unittest.TestCase):
    def test_public_schema_matches_packaged_schema(self) -> None:
        public_path = Path(__file__).resolve().parents[1] / "schemas" / "annotation.schema.json"
        public_schema = json.loads(public_path.read_text(encoding="utf-8"))
        self.assertEqual(annotation_response_schema(), public_schema)
        required = annotation_response_schema()["properties"]["annotations"]["items"]["required"]
        self.assertIn("anchor", required)
        self.assertIn("context", required)
        focus_points = annotation_response_schema()["properties"]["annotations"]["items"]["properties"]["focus_points"]
        self.assertIn("quote", focus_points["items"]["required"])


if __name__ == "__main__":
    unittest.main()
