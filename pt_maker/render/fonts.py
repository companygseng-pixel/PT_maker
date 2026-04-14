"""Font utilities — resolve color tokens and set dual latin/eastAsia typefaces.

python-pptx's :class:`~pptx.text.text.Font` does not expose the ``eastAsia``
typeface slot, so we drop down to XML to add ``<a:ea typeface="Pretendard"/>``
for Korean glyphs while keeping Latin glyphs on the Latin face.
"""

from __future__ import annotations

from typing import Any

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.text.text import _Run

_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NSMAP = {"a": _A}


def hex_to_rgb(hex_str: str) -> RGBColor:
    s = hex_str.lstrip("#")
    return RGBColor(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def resolve_color(token_or_hex: str, theme: dict[str, Any]) -> RGBColor:
    """Resolve a color token (``primary``, ``text`` …) or explicit hex string."""
    if token_or_hex.startswith("#"):
        return hex_to_rgb(token_or_hex)
    colors = theme.get("colors", {})
    value = colors.get(token_or_hex, "#000000")
    if isinstance(value, list):
        value = value[0] if value else "#000000"
    return hex_to_rgb(value)


def apply_run_fonts(
    run: _Run,
    latin: str,
    ea: str | None = None,
    size_pt: float | None = None,
    color: RGBColor | None = None,
    bold: bool | None = None,
) -> None:
    """Set Latin + East Asian typefaces on a run via direct XML manipulation."""
    if size_pt is not None:
        run.font.size = int(size_pt * 12700)  # pt → EMU
    if bold is not None:
        run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color

    rPr = run._r.get_or_add_rPr()
    # Remove any prior latin/ea nodes
    for tag in ("latin", "ea"):
        for existing in rPr.findall(f"{{{_A}}}{tag}"):
            rPr.remove(existing)
    latin_el = etree.SubElement(rPr, f"{{{_A}}}latin")
    latin_el.set("typeface", latin)
    if ea:
        ea_el = etree.SubElement(rPr, f"{{{_A}}}ea")
        ea_el.set("typeface", ea)


def ensure_paragraph_line_spacing(paragraph, line_spacing: float = 1.3) -> None:
    paragraph.line_spacing = line_spacing
