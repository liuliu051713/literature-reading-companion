"""JSON schemas used by provider adapters."""

from __future__ import annotations

import json
from importlib.resources import files


def annotation_response_schema() -> dict:
    schema_file = files("literature_reader").joinpath("data/annotation.schema.json")
    return json.loads(schema_file.read_text(encoding="utf-8"))


PAPER_MAP_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "research_question": {"type": "string"},
        "central_claim": {"type": "string"},
        "argument_map": {"type": "array", "items": {"type": "string"}},
        "scope_notes": {"type": "string"},
    },
    "required": ["title", "research_question", "central_claim", "argument_map", "scope_notes"],
}
