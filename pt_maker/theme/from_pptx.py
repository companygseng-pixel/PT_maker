"""Extract a theme JSON from a reference PPTX file.

We parse the first ``slide_master`` and a handful of ``slide_layouts`` to
recover:
  * slide dimensions
  * theme color scheme (from ``ppt/theme/theme1.xml`` via python-pptx XML)
  * primary Latin/East-Asian fonts
  * placeholder geometries grouped by layout role

The extraction is best-effort: missing data is filled from
:func:`pt_maker.theme.schema.default_theme`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.util import Emu

from .schema import default_theme

# Map python-pptx placeholder types (PP_PLACEHOLDER) → theme role names.
# (Numeric fallbacks avoid coupling to enum imports when types vary.)
_PLACEHOLDER_ROLE_MAP = {
    13: "title",       # TITLE
    15: "title",       # CENTER_TITLE
    14: "subtitle",    # SUBTITLE
    2: "body",         # BODY
    18: "body",        # OBJECT
    7: "image",        # PICTURE
    8: "chart",        # CHART
    12: "table",       # TABLE
}


def _emu_to_in(v: int | None) -> float:
    if v is None:
        return 0.0
    return round(Emu(v).inches, 3)


def _role_for(ph) -> str:
    try:
        t = int(ph.placeholder_format.type)
    except Exception:
        return "body"
    return _PLACEHOLDER_ROLE_MAP.get(t, "body")


def _extract_theme_colors(prs: Presentation) -> dict[str, Any]:
    """Pull the dk1/lt1/accent1..6 colors out of ``theme1.xml``."""
    from lxml import etree

    theme_part = None
    for part in prs.part.package.iter_parts():
        if part.partname.endswith("/theme1.xml"):
            theme_part = part
            break
    if theme_part is None:
        return {}

    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    root = etree.fromstring(theme_part.blob)
    scheme = root.find(".//a:clrScheme", ns)
    if scheme is None:
        return {}

    def _color(name: str) -> str | None:
        node = scheme.find(f"a:{name}", ns)
        if node is None:
            return None
        srgb = node.find(".//a:srgbClr", ns)
        if srgb is not None:
            return "#" + srgb.get("val", "000000").upper()
        sys = node.find(".//a:sysClr", ns)
        if sys is not None:
            return "#" + sys.get("lastClr", "000000").upper()
        return None

    out: dict[str, Any] = {}
    dk1 = _color("dk1") or "#1E1E1E"
    lt1 = _color("lt1") or "#FFFFFF"
    out["text"] = dk1
    out["background"] = lt1
    accents = [_color(f"accent{i}") for i in range(1, 7)]
    accents = [c for c in accents if c]
    if accents:
        out["primary"] = accents[0]
        if len(accents) > 1:
            out["secondary"] = accents[1]
        out["accent"] = accents[2:4]
    return out


def _extract_fonts(prs: Presentation) -> dict[str, str]:
    """Pull the major/minor font (Latin + East Asian) from ``theme1.xml``."""
    from lxml import etree

    theme_part = None
    for part in prs.part.package.iter_parts():
        if part.partname.endswith("/theme1.xml"):
            theme_part = part
            break
    if theme_part is None:
        return {}

    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    root = etree.fromstring(theme_part.blob)
    out: dict[str, str] = {}

    def _grab(tag: str, key: str) -> None:
        node = root.find(f".//a:{tag}", ns)
        if node is None:
            return
        latin = node.find("a:latin", ns)
        if latin is not None and latin.get("typeface"):
            out[f"{key}_font_latin"] = latin.get("typeface")
        ea = node.find("a:ea", ns)
        if ea is not None and ea.get("typeface"):
            out[f"{key}_font_ea"] = ea.get("typeface")

    _grab("majorFont", "title")
    _grab("minorFont", "body")
    return out


def _guess_layout_name(layout_name: str) -> str:
    """Normalize PPTX layout display names to our canonical roles."""
    n = (layout_name or "").lower()
    mapping = {
        "title slide": "title",
        "title": "title",
        "section header": "section_divider",
        "divider": "section_divider",
        "title and content": "content",
        "content": "content",
        "two content": "two_column",
        "two column": "two_column",
        "comparison": "two_column",
        "picture with caption": "image_left",
        "blank": "content",
    }
    for k, v in mapping.items():
        if k in n:
            return v
    return "content"


def extract_theme_from_pptx(path: str | Path, name: str | None = None) -> dict[str, Any]:
    """Return a theme dict derived from a reference PPTX."""
    path = Path(path)
    prs = Presentation(str(path))

    theme = default_theme(name or path.stem)
    theme["source"] = {"kind": "pptx", "path": str(path.resolve())}

    # Slide size
    theme["slide_size"] = {
        "width_in": round(Emu(prs.slide_width).inches, 3),
        "height_in": round(Emu(prs.slide_height).inches, 3),
    }

    # Colors + fonts from theme1.xml
    colors = _extract_theme_colors(prs)
    if colors:
        theme["colors"].update(colors)
    fonts = _extract_fonts(prs)
    if fonts:
        theme["typography"].update(fonts)

    # Placeholder geometries, grouped by canonical layout name
    layouts: dict[str, dict[str, Any]] = {}
    for layout in prs.slide_layouts:
        canonical = _guess_layout_name(layout.name)
        placeholders = []
        for ph in layout.placeholders:
            placeholders.append({
                "role": _role_for(ph),
                "x_in": _emu_to_in(getattr(ph, "left", None)),
                "y_in": _emu_to_in(getattr(ph, "top", None)),
                "w_in": _emu_to_in(getattr(ph, "width", None)),
                "h_in": _emu_to_in(getattr(ph, "height", None)),
                "color_token": "text",
                "align": "left",
            })
        if placeholders and canonical not in layouts:
            layouts[canonical] = {
                "placeholders": placeholders,
                "background_token": "background",
            }

    # Merge: prefer extracted, fall back to defaults
    for k, v in layouts.items():
        theme["layouts"][k] = v

    return theme
