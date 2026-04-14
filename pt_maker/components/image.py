"""Image component — insert a picture while preserving aspect ratio."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image
from pptx.util import Inches


def add_image(slide, block: dict[str, Any], theme: dict[str, Any]) -> None:
    src = block.get("image_path", "")
    if not src or not Path(src).exists():
        return

    # Fit into the given box while preserving aspect ratio
    box_w, box_h = float(block["w_in"]), float(block["h_in"])
    try:
        with Image.open(src) as im:
            iw, ih = im.size
    except Exception:
        iw, ih = 1, 1
    if iw == 0 or ih == 0:
        iw, ih = 1, 1
    img_ratio = iw / ih
    box_ratio = box_w / box_h if box_h > 0 else 1.0
    if img_ratio > box_ratio:
        w = box_w
        h = box_w / img_ratio
    else:
        h = box_h
        w = box_h * img_ratio
    x = float(block["x_in"]) + (box_w - w) / 2
    y = float(block["y_in"]) + (box_h - h) / 2

    slide.shapes.add_picture(src, Inches(x), Inches(y),
                             width=Inches(w), height=Inches(h))
