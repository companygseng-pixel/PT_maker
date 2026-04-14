"""Decorative shapes (header bars, dividers) filled from theme tokens."""

from __future__ import annotations

from typing import Any

from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches

from ..render.fonts import resolve_color


def add_shape(slide, block: dict[str, Any], theme: dict[str, Any]) -> None:
    shape_name = block.get("shape", "rectangle").upper()
    shape_type = getattr(MSO_SHAPE, shape_name, MSO_SHAPE.RECTANGLE)

    shp = slide.shapes.add_shape(
        shape_type,
        Inches(block["x_in"]), Inches(block["y_in"]),
        Inches(block["w_in"]), Inches(block["h_in"]),
    )
    shp.line.fill.background()
    fill = shp.fill
    fill.solid()
    fill.fore_color.rgb = resolve_color(block.get("fill_token", "primary"), theme)
