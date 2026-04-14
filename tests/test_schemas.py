"""Schema validation round-trips."""

from __future__ import annotations

import json

from pt_maker.outline.schema import validate_outline
from pt_maker.slides.schema import validate_slides
from pt_maker.theme.schema import default_theme, validate_theme


def test_default_theme_is_valid():
    assert validate_theme(default_theme("x")) == []


def test_theme_rejects_missing_fields():
    bad = {"name": "x"}
    errs = validate_theme(bad)
    assert errs


def test_outline_minimum_valid():
    o = {
        "meta": {"title": "t", "purpose": "business", "language": "ko"},
        "slides": [{"id": "s1", "type": "title", "title": "T"}],
    }
    assert validate_outline(o) == []


def test_outline_rejects_bad_type():
    o = {
        "meta": {"title": "t", "purpose": "business", "language": "ko"},
        "slides": [{"id": "s1", "type": "unknown"}],
    }
    assert validate_outline(o)


def test_slides_minimum_valid():
    s = {
        "meta": {},
        "theme_ref": {"name": "default"},
        "slides": [{
            "id": "s1", "layout": "content",
            "blocks": [{"kind": "text", "text": "hi",
                         "x_in": 1, "y_in": 1, "w_in": 5, "h_in": 1}],
        }],
    }
    assert validate_slides(s) == []
