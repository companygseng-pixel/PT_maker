"""Render LaTeX → PNG using matplotlib mathtext (no external LaTeX install)."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any

from pptx.util import Inches

_CACHE_DIR = Path(tempfile.gettempdir()) / "ptmaker_math_cache"


def _render_latex_to_png(latex: str, color_hex: str = "#1E1E1E",
                         dpi: int = 220) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{latex}|{color_hex}|{dpi}".encode()).hexdigest()[:16]
    out = _CACHE_DIR / f"eq_{key}.png"
    if out.exists():
        return out

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(0.01, 0.01))
    fig.patch.set_alpha(0)
    text = fig.text(0, 0, f"${latex}$", fontsize=24, color=color_hex)
    fig.savefig(out, dpi=dpi, bbox_inches="tight", pad_inches=0.05, transparent=True)
    plt.close(fig)
    return out


def add_math(slide, block: dict[str, Any], theme: dict[str, Any]) -> None:
    latex = block.get("latex", "").strip()
    if not latex:
        return
    color_hex = theme["colors"].get("text", "#1E1E1E")
    png = _render_latex_to_png(latex, color_hex=color_hex)
    slide.shapes.add_picture(
        str(png),
        Inches(block["x_in"]), Inches(block["y_in"]),
        width=Inches(block["w_in"]), height=Inches(block["h_in"]),
    )
