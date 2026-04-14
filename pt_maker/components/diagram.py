"""Mermaid / Graphviz diagrams → PNG via external CLI.

Requires ``mmdc`` (``@mermaid-js/mermaid-cli``) or ``dot`` (graphviz) on PATH.
Falls back to a plain text placeholder if the CLI is missing.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pptx.util import Inches

_CACHE_DIR = Path(tempfile.gettempdir()) / "ptmaker_diagram_cache"


def _render_mermaid(code: str) -> Path | None:
    if shutil.which("mmdc") is None:
        return None
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(code.encode("utf-8")).hexdigest()[:16]
    out = _CACHE_DIR / f"mermaid_{key}.png"
    if out.exists():
        return out
    src = _CACHE_DIR / f"mermaid_{key}.mmd"
    src.write_text(code, encoding="utf-8")
    try:
        subprocess.run(
            ["mmdc", "-i", str(src), "-o", str(out), "-b", "transparent"],
            check=True, capture_output=True, timeout=60,
        )
        return out if out.exists() else None
    except Exception:
        return None


def _render_graphviz(code: str) -> Path | None:
    if shutil.which("dot") is None:
        return None
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(code.encode("utf-8")).hexdigest()[:16]
    out = _CACHE_DIR / f"graphviz_{key}.png"
    if out.exists():
        return out
    try:
        subprocess.run(
            ["dot", "-Tpng", "-o", str(out)],
            input=code.encode("utf-8"),
            check=True, capture_output=True, timeout=60,
        )
        return out if out.exists() else None
    except Exception:
        return None


def add_diagram(slide, block: dict[str, Any], theme: dict[str, Any]) -> None:
    spec = block.get("diagram", {})
    syntax = spec.get("syntax", "mermaid")
    code = spec.get("code", "")
    if not code:
        return
    png: Path | None = None
    if syntax == "mermaid":
        png = _render_mermaid(code)
    elif syntax == "graphviz":
        png = _render_graphviz(code)
    if png is None:
        # Fall back: insert a textbox with the diagram source
        from .text import add_text_block
        add_text_block(slide, {
            **block, "text": f"[{syntax} diagram unavailable]\n{code[:400]}",
            "font_size_pt": 12, "color_token": "muted",
        }, theme)
        return
    slide.shapes.add_picture(
        str(png),
        Inches(block["x_in"]), Inches(block["y_in"]),
        width=Inches(block["w_in"]), height=Inches(block["h_in"]),
    )
