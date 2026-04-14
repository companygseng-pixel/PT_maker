"""Slide spec — the concrete render input consumed by :mod:`pt_maker.render`.

Unlike :mod:`pt_maker.outline`, this describes the *final shape* of each slide:
which theme layout to use, which component blocks to draw and where. The
drafter produces this from outline + theme; the renderer is a pure function of
it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SLIDES_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "PTMakerSlides",
    "type": "object",
    "required": ["meta", "theme_ref", "slides"],
    "properties": {
        "meta": {"type": "object"},
        "theme_ref": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "path": {"type": "string"},
            },
        },
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "layout", "blocks"],
                "properties": {
                    "id": {"type": "string"},
                    "layout": {"type": "string"},
                    "notes": {"type": "string"},
                    "blocks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["kind"],
                            "properties": {
                                "kind": {
                                    "enum": [
                                        "text", "bullets", "image",
                                        "chart", "table", "math",
                                        "icon", "diagram", "shape",
                                    ]
                                },
                                "placeholder_role": {"type": "string"},
                                # Explicit geometry (overrides placeholder).
                                "x_in": {"type": "number"},
                                "y_in": {"type": "number"},
                                "w_in": {"type": "number"},
                                "h_in": {"type": "number"},
                                # Styling
                                "font_size_pt": {"type": "number"},
                                "color_token": {"type": "string"},
                                "align": {"enum": ["left", "center", "right"]},
                                "bold": {"type": "boolean"},
                                # Payload (kind-specific)
                                "text": {"type": "string"},
                                "items": {"type": "array", "items": {"type": "string"}},
                                "image_path": {"type": "string"},
                                "chart": {"type": "object"},
                                "rows": {"type": "array"},
                                "headers": {"type": "array", "items": {"type": "string"}},
                                "latex": {"type": "string"},
                                "icon_name": {"type": "string"},
                                "diagram": {
                                    "type": "object",
                                    "properties": {
                                        "syntax": {"enum": ["mermaid", "graphviz"]},
                                        "code": {"type": "string"},
                                    },
                                },
                                "shape": {"type": "string"},
                                "fill_token": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}

_VALIDATOR = Draft202012Validator(SLIDES_SCHEMA)


def validate_slides(spec: dict[str, Any]) -> list[str]:
    return [f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}"
            for e in _VALIDATOR.iter_errors(spec)]


def load_slides(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    errors = validate_slides(data)
    if errors:
        raise ValueError("Invalid slides spec:\n  " + "\n  ".join(errors))
    return data


def save_slides(spec: dict[str, Any], path: str | Path) -> Path:
    errors = validate_slides(spec)
    if errors:
        raise ValueError("Refusing to save invalid slides spec:\n  " + "\n  ".join(errors))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    return p
