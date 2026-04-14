"""Extract a theme JSON from a reference PDF by rasterizing the cover page(s)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from .from_image import extract_theme_from_image


def extract_theme_from_pdf(
    path: str | Path,
    name: str | None = None,
    page_index: int = 0,
    dpi: int = 200,
    use_vision: bool = True,
) -> dict[str, Any]:
    path = Path(path)
    doc = fitz.open(str(path))
    if page_index >= len(doc):
        page_index = 0
    page = doc[page_index]
    pix = page.get_pixmap(dpi=dpi)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    pix.save(str(tmp_path))
    doc.close()

    theme = extract_theme_from_image(tmp_path, name=name or path.stem, use_vision=use_vision)
    theme["source"] = {"kind": "pdf", "path": str(path.resolve())}
    return theme
