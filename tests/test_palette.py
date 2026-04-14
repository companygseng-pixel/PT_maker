"""Palette classification heuristic."""

from __future__ import annotations

from pt_maker.theme.palette import classify_palette


def test_classify_palette_assigns_bg_and_text():
    # Frequency-sorted hex palette: near-white, near-black, saturated blue, green
    pal = ["#FFFFFF", "#111111", "#1E88E5", "#43A047", "#F4B400", "#CCCCCC"]
    out = classify_palette(pal)
    assert out["background"] == "#FFFFFF"
    assert out["text"] == "#111111"
    assert out["primary"] in pal
    assert "surface" in out
    assert "muted" in out
