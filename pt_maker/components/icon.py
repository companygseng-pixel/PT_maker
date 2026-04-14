"""Lucide icon insertion.

Lucide ships plain SVG; we download on demand, rasterize to PNG via Pillow
(with cairosvg if available — falls back to SVG-as-bitmap).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import requests
from pptx.util import Inches

_CACHE_DIR = Path.home() / ".cache" / "ptmaker" / "icons"
_LUCIDE_BASE = "https://cdn.jsdelivr.net/npm/lucide-static@latest/icons"


def _fetch_icon_svg(name: str) -> Path | None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    svg_path = _CACHE_DIR / f"{name}.svg"
    if svg_path.exists():
        return svg_path
    try:
        r = requests.get(f"{_LUCIDE_BASE}/{name}.svg", timeout=10)
        if r.status_code != 200:
            return None
        svg_path.write_bytes(r.content)
        return svg_path
    except Exception:
        return None


def _svg_to_png(svg_path: Path, color_hex: str, size_px: int = 256) -> Path | None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{svg_path.name}|{color_hex}|{size_px}".encode()).hexdigest()[:12]
    out = _CACHE_DIR / f"{svg_path.stem}_{key}.png"
    if out.exists():
        return out

    try:
        import cairosvg
    except ImportError:
        return None

    # Recolor: replace currentColor in Lucide SVGs
    svg = svg_path.read_text(encoding="utf-8")
    svg = svg.replace("currentColor", color_hex)
    cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                     write_to=str(out),
                     output_width=size_px, output_height=size_px)
    return out


def add_icon(slide, block: dict[str, Any], theme: dict[str, Any]) -> None:
    name = block.get("icon_name", "").strip()
    if not name:
        return
    color_hex = _resolve_color_hex(block.get("color_token", "primary"), theme)
    svg = _fetch_icon_svg(name)
    if svg is None:
        return
    png = _svg_to_png(svg, color_hex)
    if png is None:
        # Fallback: insert SVG as picture (PPTX supports SVG via images in modern builds)
        png = svg
    slide.shapes.add_picture(
        str(png),
        Inches(block["x_in"]), Inches(block["y_in"]),
        width=Inches(block["w_in"]), height=Inches(block["h_in"]),
    )


def _resolve_color_hex(token: str, theme: dict[str, Any]) -> str:
    if token.startswith("#"):
        return token
    c = theme.get("colors", {}).get(token, "#000000")
    if isinstance(c, list):
        c = c[0] if c else "#000000"
    return c
