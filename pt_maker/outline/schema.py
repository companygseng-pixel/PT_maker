"""Outline data model — intermediate structure between ingestion and drafting.

A :class:`DeckOutline` describes *what* should be on each slide in plain
narrative form. It is purpose-aware (academic / IR / business) and carries
per-slide provenance (source_page) for traceability.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

OUTLINE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "PTMakerDeckOutline",
    "type": "object",
    "required": ["meta", "slides"],
    "properties": {
        "meta": {
            "type": "object",
            "required": ["title", "purpose", "language"],
            "properties": {
                "title": {"type": "string"},
                "subtitle": {"type": "string"},
                "authors": {"type": "array", "items": {"type": "string"}},
                "date": {"type": "string"},
                "purpose": {"enum": ["academic", "ir", "business"]},
                "audience": {"type": "string"},
                "duration_min": {"type": "number"},
                "language": {"enum": ["ko", "en"]},
                "source_pdf": {"type": "string"},
            },
        },
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "type"],
                "properties": {
                    "id": {"type": "string"},
                    "type": {
                        "enum": [
                            "title", "agenda", "section", "content",
                            "chart", "table", "figure", "equation",
                            "diagram", "quote", "closing",
                        ]
                    },
                    "title": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                    "items": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "string"},
                    "source_page": {"type": "integer"},

                    # chart
                    "chart": {
                        "type": "object",
                        "properties": {
                            "kind": {"enum": ["bar", "column", "line", "pie", "scatter"]},
                            "data": {"type": "object"},
                            "x_title": {"type": "string"},
                            "y_title": {"type": "string"},
                        },
                    },

                    # table
                    "rows": {"type": "array"},
                    "headers": {"type": "array", "items": {"type": "string"}},

                    # figure
                    "image_ref": {"type": "string"},
                    "caption": {"type": "string"},

                    # equation
                    "latex": {"type": "string"},
                    "explanation": {"type": "string"},

                    # diagram
                    "syntax": {"enum": ["mermaid", "graphviz"]},
                    "code": {"type": "string"},

                    # quote
                    "quote_text": {"type": "string"},
                    "attribution": {"type": "string"},
                },
            },
        },
    },
}

_VALIDATOR = Draft202012Validator(OUTLINE_SCHEMA)


def validate_outline(outline: dict[str, Any]) -> list[str]:
    return [f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}"
            for e in _VALIDATOR.iter_errors(outline)]


def load_outline(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    errors = validate_outline(data)
    if errors:
        raise ValueError("Invalid outline:\n  " + "\n  ".join(errors))
    return data


def save_outline(outline: dict[str, Any], path: str | Path) -> Path:
    errors = validate_outline(outline)
    if errors:
        raise ValueError("Refusing to save invalid outline:\n  " + "\n  ".join(errors))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(outline, f, ensure_ascii=False, indent=2)
    return p
