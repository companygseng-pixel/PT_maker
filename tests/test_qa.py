"""QA smoke tests: contrast, overflow, numeric traceability."""

from __future__ import annotations

from pt_maker.qa.checks import contrast_ratio, estimate_overflow, run_qa
from pt_maker.theme.schema import default_theme


def test_contrast_white_on_black():
    assert contrast_ratio("#FFFFFF", "#000000") > 20


def test_contrast_low_pair():
    assert contrast_ratio("#EEEEEE", "#FFFFFF") < 2


def test_overflow_large_box_no_overflow():
    assert estimate_overflow("hi", 10.0, 5.0, 18) is False


def test_overflow_tiny_box_overflows():
    assert estimate_overflow("a very long sentence " * 50, 2.0, 0.5, 18) is True


def test_run_qa_catches_low_contrast():
    theme = default_theme("t")
    # Force low-contrast foreground via explicit color token
    theme["colors"]["text"] = "#EFEFEF"
    spec = {
        "meta": {}, "theme_ref": {"name": "t"},
        "slides": [{"id": "s1", "layout": "content",
                    "blocks": [{"kind": "text", "text": "hi",
                                "x_in": 1, "y_in": 1, "w_in": 5, "h_in": 1,
                                "font_size_pt": 18, "color_token": "text"}]}],
    }
    r = run_qa(spec, theme)
    assert any(w["kind"] == "low_contrast" for w in r.warnings)


def test_run_qa_catches_unsourced_number():
    theme = default_theme("t")
    spec = {
        "meta": {}, "theme_ref": {"name": "t"},
        "slides": [{"id": "s1", "layout": "content",
                    "blocks": [{"kind": "text", "text": "revenue 999%",
                                "x_in": 1, "y_in": 1, "w_in": 5, "h_in": 1}]}],
    }
    r = run_qa(spec, theme, source_text="revenue grew last year")
    assert any(w["kind"] == "unsourced_number" for w in r.warnings)
