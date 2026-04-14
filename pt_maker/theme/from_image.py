"""Extract a theme JSON from a single reference image (or rendered PDF page).

Uses k-means palette extraction for color, and optionally Claude Vision for
layout/typography inference. If the Anthropic SDK or API key is unavailable,
falls back gracefully to palette-only theming.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from .palette import classify_palette, extract_palette
from .schema import default_theme

_VISION_SYSTEM = (
    "You are a senior presentation designer. Given a reference slide image, "
    "output a concise JSON describing the visual system. Do not invent colors "
    "that aren't in the image. Respond with JSON only."
)

_VISION_USER = """\
Analyze this reference slide and return a JSON object with:
{
  "title_font_style": "serif" | "sans" | "display" | "mono",
  "body_font_style":  "serif" | "sans" | "display" | "mono",
  "title_size_pt": number,
  "body_size_pt": number,
  "has_header_bar": boolean,
  "has_footer": boolean,
  "accent_role_hints": ["primary", "secondary", ...],
  "notes": "<=1 sentence about overall mood>"
}
Respond with JSON only."""


def _vision_analyze(image_path: Path) -> dict[str, Any] | None:
    """Call Claude Vision if available; return parsed JSON or None."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    client = anthropic.Anthropic(api_key=api_key)
    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    media_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

    try:
        resp = client.messages.create(
            model=os.environ.get("PTMAKER_VISION_MODEL", "claude-opus-4-6"),
            max_tokens=800,
            system=_VISION_SYSTEM,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64",
                                                  "media_type": media_type,
                                                  "data": b64}},
                    {"type": "text", "text": _VISION_USER},
                ],
            }],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        # Extract first JSON object in response
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def extract_theme_from_image(
    path: str | Path,
    name: str | None = None,
    use_vision: bool = True,
) -> dict[str, Any]:
    path = Path(path)
    theme = default_theme(name or path.stem)
    theme["source"] = {"kind": "image", "path": str(path.resolve())}

    palette = extract_palette(path, k=6)
    theme["colors"].update(classify_palette(palette))

    if use_vision:
        vision = _vision_analyze(path)
        if vision:
            # Map font styles → concrete families
            style_map = {
                "serif":   ("Source Serif Pro", "Noto Serif KR"),
                "sans":    ("Inter", "Pretendard"),
                "display": ("Playfair Display", "Pretendard"),
                "mono":    ("JetBrains Mono", "D2Coding"),
            }
            tstyle = vision.get("title_font_style", "sans")
            bstyle = vision.get("body_font_style", "sans")
            tl, te = style_map.get(tstyle, style_map["sans"])
            bl, be = style_map.get(bstyle, style_map["sans"])
            theme["typography"]["title_font_latin"] = tl
            theme["typography"]["title_font_ea"] = te
            theme["typography"]["body_font_latin"] = bl
            theme["typography"]["body_font_ea"] = be
            if vision.get("title_size_pt"):
                theme["typography"]["sizes_pt"]["title"] = float(vision["title_size_pt"])
            if vision.get("body_size_pt"):
                theme["typography"]["sizes_pt"]["body"] = float(vision["body_size_pt"])
            if vision.get("has_header_bar"):
                theme["decorations"]["header_bar"]["enabled"] = True
            if vision.get("has_footer") is False:
                theme["decorations"]["footer"]["enabled"] = False

    return theme
