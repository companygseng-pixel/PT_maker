"""Theme data model and JSON schema.

A theme captures everything needed to reproduce a deck's visual identity:
slide geometry, palette, typography, placeholder layouts, and decorations.
Produced by :mod:`pt_maker.theme.from_pptx` / ``from_pdf`` / ``from_image``
and consumed by :mod:`pt_maker.render`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

# ---------------------------------------------------------------------------
# JSON Schema
# ---------------------------------------------------------------------------

THEME_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "PTMakerTheme",
    "type": "object",
    "required": ["name", "slide_size", "colors", "typography", "layouts"],
    "properties": {
        "name": {"type": "string"},
        "source": {
            "type": "object",
            "properties": {
                "kind": {"enum": ["pptx", "pdf", "image", "manual"]},
                "path": {"type": "string"},
            },
        },
        "slide_size": {
            "type": "object",
            "required": ["width_in", "height_in"],
            "properties": {
                "width_in": {"type": "number", "minimum": 1},
                "height_in": {"type": "number", "minimum": 1},
            },
        },
        "colors": {
            "type": "object",
            "required": ["primary", "background", "text"],
            "properties": {
                "primary": {"type": "string"},
                "secondary": {"type": "string"},
                "accent": {"type": "array", "items": {"type": "string"}},
                "background": {"type": "string"},
                "surface": {"type": "string"},
                "text": {"type": "string"},
                "muted": {"type": "string"},
            },
        },
        "typography": {
            "type": "object",
            "required": ["body_font_latin", "sizes_pt"],
            "properties": {
                "title_font_latin": {"type": "string"},
                "title_font_ea": {"type": "string"},
                "body_font_latin": {"type": "string"},
                "body_font_ea": {"type": "string"},
                "mono": {"type": "string"},
                "sizes_pt": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "number"},
                        "heading": {"type": "number"},
                        "body": {"type": "number"},
                        "caption": {"type": "number"},
                    },
                },
            },
        },
        "layouts": {
            "type": "object",
            "description": "Per-layout placeholder definitions.",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "placeholders": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["role", "x_in", "y_in", "w_in", "h_in"],
                            "properties": {
                                "role": {"type": "string"},
                                "x_in": {"type": "number"},
                                "y_in": {"type": "number"},
                                "w_in": {"type": "number"},
                                "h_in": {"type": "number"},
                                "font_size_pt": {"type": "number"},
                                "color_token": {"type": "string"},
                                "align": {"enum": ["left", "center", "right"]},
                            },
                        },
                    },
                    "background_token": {"type": "string"},
                },
            },
        },
        "decorations": {
            "type": "object",
            "properties": {
                "logo_path": {"type": "string"},
                "header_bar": {"type": "object"},
                "footer": {"type": "object"},
            },
        },
    },
}

_VALIDATOR = Draft202012Validator(THEME_SCHEMA)


# ---------------------------------------------------------------------------
# Dataclasses (lightweight wrappers — dicts are the source of truth)
# ---------------------------------------------------------------------------


@dataclass
class Placeholder:
    role: str
    x_in: float
    y_in: float
    w_in: float
    h_in: float
    font_size_pt: float | None = None
    color_token: str = "text"
    align: str = "left"


@dataclass
class Layout:
    placeholders: list[Placeholder] = field(default_factory=list)
    background_token: str = "background"


DEFAULT_LAYOUT_NAMES = (
    "title",
    "section_divider",
    "content",
    "two_column",
    "image_left",
    "chart_full",
    "quote",
    "closing",
)


def default_theme(name: str = "default") -> dict[str, Any]:
    """A sane built-in fallback theme used when extraction fails."""
    return {
        "name": name,
        "source": {"kind": "manual", "path": ""},
        "slide_size": {"width_in": 13.333, "height_in": 7.5},
        "colors": {
            "primary": "#0A3D62",
            "secondary": "#60A3BC",
            "accent": ["#F6B93B", "#EB2F06"],
            "background": "#FFFFFF",
            "surface": "#F2F2F2",
            "text": "#1E1E1E",
            "muted": "#6C6C6C",
        },
        "typography": {
            "title_font_latin": "Inter",
            "title_font_ea": "Pretendard",
            "body_font_latin": "Inter",
            "body_font_ea": "Pretendard",
            "mono": "JetBrains Mono",
            "sizes_pt": {"title": 40, "heading": 28, "body": 18, "caption": 12},
        },
        "layouts": {
            "title": {
                "placeholders": [
                    {"role": "title", "x_in": 0.8, "y_in": 2.6, "w_in": 11.7, "h_in": 1.6,
                     "font_size_pt": 48, "color_token": "primary", "align": "left"},
                    {"role": "subtitle", "x_in": 0.8, "y_in": 4.3, "w_in": 11.7, "h_in": 0.8,
                     "font_size_pt": 22, "color_token": "muted", "align": "left"},
                ],
                "background_token": "background",
            },
            "section_divider": {
                "placeholders": [
                    {"role": "title", "x_in": 0.8, "y_in": 3.0, "w_in": 11.7, "h_in": 1.5,
                     "font_size_pt": 44, "color_token": "background", "align": "left"},
                ],
                "background_token": "primary",
            },
            "content": {
                "placeholders": [
                    {"role": "title", "x_in": 0.6, "y_in": 0.5, "w_in": 12.1, "h_in": 0.9,
                     "font_size_pt": 28, "color_token": "primary", "align": "left"},
                    {"role": "body", "x_in": 0.6, "y_in": 1.6, "w_in": 12.1, "h_in": 5.5,
                     "font_size_pt": 18, "color_token": "text", "align": "left"},
                ],
                "background_token": "background",
            },
            "two_column": {
                "placeholders": [
                    {"role": "title", "x_in": 0.6, "y_in": 0.5, "w_in": 12.1, "h_in": 0.9,
                     "font_size_pt": 28, "color_token": "primary", "align": "left"},
                    {"role": "body_left", "x_in": 0.6, "y_in": 1.6, "w_in": 5.9, "h_in": 5.5,
                     "font_size_pt": 18, "color_token": "text", "align": "left"},
                    {"role": "body_right", "x_in": 6.8, "y_in": 1.6, "w_in": 5.9, "h_in": 5.5,
                     "font_size_pt": 18, "color_token": "text", "align": "left"},
                ],
                "background_token": "background",
            },
            "image_left": {
                "placeholders": [
                    {"role": "title", "x_in": 0.6, "y_in": 0.5, "w_in": 12.1, "h_in": 0.9,
                     "font_size_pt": 28, "color_token": "primary", "align": "left"},
                    {"role": "image", "x_in": 0.6, "y_in": 1.6, "w_in": 6.2, "h_in": 5.5},
                    {"role": "body", "x_in": 7.1, "y_in": 1.6, "w_in": 5.6, "h_in": 5.5,
                     "font_size_pt": 18, "color_token": "text", "align": "left"},
                ],
                "background_token": "background",
            },
            "chart_full": {
                "placeholders": [
                    {"role": "title", "x_in": 0.6, "y_in": 0.5, "w_in": 12.1, "h_in": 0.9,
                     "font_size_pt": 28, "color_token": "primary", "align": "left"},
                    {"role": "chart", "x_in": 0.6, "y_in": 1.6, "w_in": 12.1, "h_in": 5.5},
                ],
                "background_token": "background",
            },
            "quote": {
                "placeholders": [
                    {"role": "quote", "x_in": 1.2, "y_in": 2.5, "w_in": 10.9, "h_in": 2.5,
                     "font_size_pt": 32, "color_token": "primary", "align": "left"},
                    {"role": "attribution", "x_in": 1.2, "y_in": 5.2, "w_in": 10.9, "h_in": 0.6,
                     "font_size_pt": 16, "color_token": "muted", "align": "left"},
                ],
                "background_token": "surface",
            },
            "closing": {
                "placeholders": [
                    {"role": "title", "x_in": 0.8, "y_in": 3.0, "w_in": 11.7, "h_in": 1.6,
                     "font_size_pt": 48, "color_token": "primary", "align": "center"},
                    {"role": "subtitle", "x_in": 0.8, "y_in": 4.7, "w_in": 11.7, "h_in": 0.8,
                     "font_size_pt": 20, "color_token": "muted", "align": "center"},
                ],
                "background_token": "background",
            },
        },
        "decorations": {
            "logo_path": "",
            "header_bar": {"height_in": 0.3, "fill_token": "primary", "enabled": False},
            "footer": {"text": "", "page_number": True, "enabled": True},
        },
    }


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def validate_theme(theme: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors (empty if valid)."""
    return [f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}"
            for e in _VALIDATOR.iter_errors(theme)]


def load_theme(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    errors = validate_theme(data)
    if errors:
        raise ValueError("Invalid theme:\n  " + "\n  ".join(errors))
    return data


def save_theme(theme: dict[str, Any], path: str | Path) -> Path:
    errors = validate_theme(theme)
    if errors:
        raise ValueError("Refusing to save invalid theme:\n  " + "\n  ".join(errors))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(theme, f, ensure_ascii=False, indent=2)
    return p


def asdict_placeholder(ph: Placeholder) -> dict[str, Any]:
    return asdict(ph)
