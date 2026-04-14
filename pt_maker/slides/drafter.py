"""Outline + theme → concrete slides spec.

The drafter has two modes:
1. ``draft_slides_llm`` — call Claude to do smart layout mapping, rewording
   for presentation voice, chart styling, icon/diagram suggestions.
2. ``draft_slides_rule`` — a pure-Python fallback used when no API key is
   present; maps outline types to canonical layouts with default blocks.

Both produce output conforming to :mod:`pt_maker.slides.schema`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..llm import call_json

_SYSTEM = """\
You translate a deck outline into a slide spec for a PPTX renderer. For each \
outline slide you choose a layout from the provided theme and emit a list of \
`blocks`. You respect the theme palette (by token) and never hard-code colors.
Respond with JSON only."""


# ---------------------------------------------------------------------------
# Rule-based fallback
# ---------------------------------------------------------------------------

_LAYOUT_FOR_TYPE = {
    "title": "title",
    "agenda": "content",
    "section": "section_divider",
    "content": "content",
    "chart": "chart_full",
    "table": "content",
    "figure": "image_left",
    "equation": "content",
    "diagram": "chart_full",
    "quote": "quote",
    "closing": "closing",
}


def _placeholder(layout: dict[str, Any], role: str) -> dict[str, Any] | None:
    for ph in layout.get("placeholders", []):
        if ph.get("role") == role:
            return ph
    return None


def draft_slides_rule(outline: dict[str, Any], theme: dict[str, Any]) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "meta": outline.get("meta", {}),
        "theme_ref": {"name": theme["name"]},
        "slides": [],
    }
    for s in outline.get("slides", []):
        layout_name = _LAYOUT_FOR_TYPE.get(s.get("type", "content"), "content")
        layout = theme["layouts"].get(layout_name) or theme["layouts"]["content"]
        blocks: list[dict[str, Any]] = []

        # Title
        title_ph = _placeholder(layout, "title")
        if s.get("title") and title_ph:
            blocks.append({
                "kind": "text", "placeholder_role": "title",
                "text": s["title"],
            })

        # Subtitle (for title/closing)
        sub_ph = _placeholder(layout, "subtitle")
        if s.get("subtitle") and sub_ph:
            blocks.append({
                "kind": "text", "placeholder_role": "subtitle",
                "text": s["subtitle"],
            })

        t = s.get("type")
        if t in ("content", "agenda"):
            body_role = "body"
            items = s.get("bullets") or s.get("items") or []
            if items:
                blocks.append({
                    "kind": "bullets", "placeholder_role": body_role,
                    "items": items,
                })
        elif t == "chart":
            blocks.append({
                "kind": "chart", "placeholder_role": "chart",
                "chart": s.get("chart", {}),
            })
        elif t == "table":
            ph = _placeholder(layout, "body") or {}
            blocks.append({
                "kind": "table",
                "x_in": ph.get("x_in", 0.6), "y_in": ph.get("y_in", 1.6),
                "w_in": ph.get("w_in", 12.1), "h_in": ph.get("h_in", 5.5),
                "headers": s.get("headers") or (s.get("rows", [[]])[0] if s.get("rows") else []),
                "rows": s.get("rows", [])[1:] if s.get("headers") is None and s.get("rows") else s.get("rows", []),
            })
        elif t == "figure":
            blocks.append({
                "kind": "image", "placeholder_role": "image",
                "image_path": s.get("image_ref", ""),
            })
            if s.get("caption"):
                body_ph = _placeholder(layout, "body")
                if body_ph:
                    blocks.append({
                        "kind": "text", "placeholder_role": "body",
                        "text": s["caption"], "font_size_pt": 14, "color_token": "muted",
                    })
        elif t == "equation":
            body_ph = _placeholder(layout, "body") or {}
            blocks.append({
                "kind": "math",
                "x_in": body_ph.get("x_in", 1.0), "y_in": body_ph.get("y_in", 2.0),
                "w_in": body_ph.get("w_in", 11.0), "h_in": 2.0,
                "latex": s.get("latex", ""),
            })
            if s.get("explanation"):
                blocks.append({
                    "kind": "text",
                    "x_in": body_ph.get("x_in", 1.0), "y_in": 4.5,
                    "w_in": body_ph.get("w_in", 11.0), "h_in": 1.5,
                    "text": s["explanation"], "font_size_pt": 16,
                })
        elif t == "diagram":
            ph = _placeholder(layout, "chart") or _placeholder(layout, "body") or {}
            blocks.append({
                "kind": "diagram",
                "x_in": ph.get("x_in", 1.0), "y_in": ph.get("y_in", 1.6),
                "w_in": ph.get("w_in", 11.0), "h_in": ph.get("h_in", 5.0),
                "diagram": {"syntax": s.get("syntax", "mermaid"),
                             "code": s.get("code", "")},
            })
        elif t == "quote":
            q_ph = _placeholder(layout, "quote") or {}
            blocks.append({
                "kind": "text",
                "x_in": q_ph.get("x_in", 1.2), "y_in": q_ph.get("y_in", 2.5),
                "w_in": q_ph.get("w_in", 10.9), "h_in": q_ph.get("h_in", 2.5),
                "text": f"“{s.get('quote_text', '')}”",
                "font_size_pt": 32, "color_token": "primary",
            })
            if s.get("attribution"):
                blocks.append({
                    "kind": "text",
                    "x_in": q_ph.get("x_in", 1.2), "y_in": 5.2,
                    "w_in": q_ph.get("w_in", 10.9), "h_in": 0.6,
                    "text": f"— {s['attribution']}",
                    "font_size_pt": 16, "color_token": "muted",
                })

        spec["slides"].append({
            "id": s.get("id", f"s{len(spec['slides']) + 1}"),
            "layout": layout_name,
            "notes": s.get("notes", ""),
            "blocks": blocks,
        })

    return spec


# ---------------------------------------------------------------------------
# LLM-driven drafter
# ---------------------------------------------------------------------------


def draft_slides_llm(outline: dict[str, Any], theme: dict[str, Any]) -> dict[str, Any]:
    theme_summary = {
        "name": theme["name"],
        "slide_size": theme["slide_size"],
        "colors": theme["colors"],
        "typography": theme["typography"],
        "layouts": {
            name: {"placeholders": [ph.get("role") for ph in lay.get("placeholders", [])]}
            for name, lay in theme["layouts"].items()
        },
    }

    user = f"""\
THEME:
{json.dumps(theme_summary, ensure_ascii=False, indent=2)}

OUTLINE:
{json.dumps(outline, ensure_ascii=False, indent=2)}

Produce a slides JSON where each slide has:
- id, layout (one of theme.layouts), notes, blocks[]
- Each block: kind in [text, bullets, image, chart, table, math, icon, diagram, shape]
- Prefer `placeholder_role` referring to the chosen layout's placeholders.
- Use color tokens (primary/secondary/text/muted/accent) NEVER hex.
- Rewrite outline bullets in concise presentation voice. Keep numbers verbatim.
- For IR/academic decks add one icon block per content slide (lucide icon name).
- Output JSON with top-level: meta, theme_ref, slides. No prose.
"""
    # Cache the theme summary as it's reused across slide drafting.
    return call_json(
        system=_SYSTEM,
        user=user,
        max_tokens=8192,
        extra_system_cached=json.dumps(theme_summary),
    )


def draft_slides(outline: dict[str, Any], theme: dict[str, Any],
                 use_llm: bool = True) -> dict[str, Any]:
    if use_llm:
        try:
            spec = draft_slides_llm(outline, theme)
            spec.setdefault("theme_ref", {"name": theme["name"]})
            return spec
        except Exception:
            pass
    return draft_slides_rule(outline, theme)
