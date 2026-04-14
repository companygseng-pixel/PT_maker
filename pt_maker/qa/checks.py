"""Automatic QA: overflow, contrast, font presence, numeric traceability."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QAReport:
    warnings: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_warn(self, kind: str, slide_id: str, message: str, **extra) -> None:
        self.warnings.append({"kind": kind, "slide_id": slide_id,
                               "message": message, **extra})

    def add_err(self, kind: str, slide_id: str, message: str, **extra) -> None:
        self.errors.append({"kind": kind, "slide_id": slide_id,
                             "message": message, **extra})

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "warnings": self.warnings, "errors": self.errors}


# ---------------------------------------------------------------------------
# Contrast (WCAG AA)
# ---------------------------------------------------------------------------


def _relative_luminance(hex_str: str) -> float:
    s = hex_str.lstrip("#")
    r, g, b = int(s[0:2], 16) / 255, int(s[2:4], 16) / 255, int(s[4:6], 16) / 255

    def ch(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast_ratio(fg: str, bg: str) -> float:
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# Overflow estimation (Pillow)
# ---------------------------------------------------------------------------


def estimate_overflow(text: str, w_in: float, h_in: float, font_size_pt: float,
                       font_path: str | None = None, line_spacing: float = 1.3) -> bool:
    """Return True if text would overflow the given box.

    Uses Pillow with a best-effort font fallback. Without a bundled TTF we fall
    back to a rough characters-per-inch estimate.
    """
    # Rough estimate: 1pt ≈ 1/72 inch; Korean/ASCII average advance ~0.55em
    try:
        from PIL import ImageFont
        font = None
        if font_path:
            font = ImageFont.truetype(font_path, int(font_size_pt))
        if font is None:
            return _overflow_estimate_rough(text, w_in, h_in, font_size_pt, line_spacing)
        avg_adv_px = font.getlength("가나다라마") / 5
        px_per_in = 96
        max_chars_per_line = max(1, int((w_in * px_per_in) / avg_adv_px))
        lines = _wrap_char_count(text, max_chars_per_line)
        line_height_in = (font_size_pt / 72.0) * line_spacing
        return (len(lines) * line_height_in) > h_in
    except Exception:
        return _overflow_estimate_rough(text, w_in, h_in, font_size_pt, line_spacing)


def _wrap_char_count(text: str, max_chars: int) -> list[str]:
    lines: list[str] = []
    for para in text.splitlines() or [text]:
        while len(para) > max_chars:
            lines.append(para[:max_chars])
            para = para[max_chars:]
        lines.append(para)
    return lines


def _overflow_estimate_rough(text: str, w_in: float, h_in: float,
                              font_size_pt: float, line_spacing: float) -> bool:
    em_in = font_size_pt / 72.0
    chars_per_line = max(1, int(w_in / (em_in * 0.55)))
    n_lines = sum(max(1, -(-len(line) // chars_per_line)) for line in text.splitlines() or [text])
    return (n_lines * em_in * line_spacing) > h_in


# ---------------------------------------------------------------------------
# Font presence (fc-list)
# ---------------------------------------------------------------------------


def fonts_available(names: list[str]) -> dict[str, bool]:
    if shutil.which("fc-list") is None:
        return {n: True for n in names}  # Can't check; assume yes
    try:
        out = subprocess.check_output(["fc-list", ":", "family"], text=True, timeout=5)
    except Exception:
        return {n: True for n in names}
    installed = {line.split(",")[0].strip().lower() for line in out.splitlines()}
    return {n: (n.lower() in installed) for n in names}


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------


_NUM_RE = re.compile(r"-?\d+(?:[,\.]\d+)*%?")


def run_qa(spec: dict[str, Any], theme: dict[str, Any],
            source_text: str | None = None) -> QAReport:
    report = QAReport()
    colors = theme.get("colors", {})
    typo = theme.get("typography", {})
    body_font = typo.get("body_font_latin", "Inter")

    # Font presence
    wanted = [typo.get("title_font_latin", "Inter"),
              typo.get("title_font_ea", "Pretendard"),
              typo.get("body_font_latin", "Inter"),
              typo.get("body_font_ea", "Pretendard")]
    wanted = [w for w in wanted if w]
    for name, present in fonts_available(list(set(wanted))).items():
        if not present:
            report.add_warn("font_missing", "*",
                            f"Font not found on system: {name}",
                            font=name)

    for s in spec.get("slides", []):
        layout_name = s.get("layout", "content")
        layout_bg_token = theme["layouts"].get(layout_name, {}).get("background_token",
                                                                      "background")
        bg_hex = _resolve_hex(layout_bg_token, colors)

        for blk in s.get("blocks", []):
            # Contrast
            if blk.get("kind") in ("text", "bullets"):
                fg_token = blk.get("color_token", "text")
                fg_hex = _resolve_hex(fg_token, colors)
                ratio = contrast_ratio(fg_hex, bg_hex)
                if ratio < 4.5:
                    report.add_warn("low_contrast", s["id"],
                                    f"Contrast {ratio:.2f}:1 < AA 4.5:1",
                                    fg=fg_hex, bg=bg_hex)

            # Overflow (rough)
            if blk.get("kind") in ("text", "bullets"):
                text = blk.get("text", "") or "\n".join(blk.get("items", []) or [])
                if text and "w_in" in blk and "h_in" in blk:
                    size = float(blk.get("font_size_pt",
                                          typo.get("sizes_pt", {}).get("body", 18)))
                    if estimate_overflow(text, blk["w_in"], blk["h_in"], size):
                        report.add_warn("overflow", s["id"],
                                        f"Text likely overflows box "
                                        f"({blk['w_in']:.1f}x{blk['h_in']:.1f}in, "
                                        f"{size}pt)")

            # Numeric traceability
            if source_text is not None and blk.get("kind") in ("text", "bullets"):
                text = blk.get("text", "") or " ".join(blk.get("items", []) or [])
                for num in _NUM_RE.findall(text):
                    if len(num) >= 2 and num not in source_text:
                        report.add_warn("unsourced_number", s["id"],
                                        f"Number '{num}' not found in source",
                                        number=num)
    return report


def _resolve_hex(token: str, colors: dict[str, Any]) -> str:
    if token.startswith("#"):
        return token
    v = colors.get(token, "#000000")
    if isinstance(v, list):
        v = v[0] if v else "#000000"
    return v
