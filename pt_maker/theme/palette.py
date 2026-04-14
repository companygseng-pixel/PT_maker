"""Palette extraction via k-means over image pixels."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def extract_palette(image_path: str | Path, k: int = 6, sample: int = 40_000) -> list[str]:
    """Return up to ``k`` dominant colors as ``#RRGGBB`` strings, frequency-sorted."""
    from sklearn.cluster import KMeans

    img = Image.open(image_path).convert("RGB")
    # Downscale large images to keep clustering fast.
    img.thumbnail((800, 800))
    arr = np.asarray(img).reshape(-1, 3)
    if arr.shape[0] > sample:
        idx = np.random.default_rng(0).choice(arr.shape[0], sample, replace=False)
        arr = arr[idx]

    km = KMeans(n_clusters=k, n_init=4, random_state=0).fit(arr)
    labels, counts = np.unique(km.labels_, return_counts=True)
    order = np.argsort(-counts)
    centers = km.cluster_centers_.astype(int)[labels][order]
    return [_hex(tuple(int(c) for c in row)) for row in centers]


def classify_palette(palette: list[str]) -> dict[str, str | list[str]]:
    """Assign rough semantic roles to a frequency-sorted palette.

    Heuristic:
      - lightest color → ``background``
      - darkest color → ``text``
      - most chromatic → ``primary``
      - next chromatic → ``secondary``
      - remaining → ``accent``
    """
    rgbs = [_parse_hex(h) for h in palette]

    def luminance(rgb: tuple[int, int, int]) -> float:
        r, g, b = rgb
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def chroma(rgb: tuple[int, int, int]) -> float:
        return max(rgb) - min(rgb)

    by_lum = sorted(range(len(rgbs)), key=lambda i: luminance(rgbs[i]))
    by_chroma = sorted(range(len(rgbs)), key=lambda i: -chroma(rgbs[i]))

    background_i = by_lum[-1]
    text_i = by_lum[0]
    chromatic = [i for i in by_chroma if i not in (background_i, text_i)]
    primary_i = chromatic[0] if chromatic else by_lum[-2]
    secondary_i = chromatic[1] if len(chromatic) > 1 else primary_i
    accent_is = chromatic[2:4]

    return {
        "background": palette[background_i],
        "text": palette[text_i],
        "primary": palette[primary_i],
        "secondary": palette[secondary_i],
        "accent": [palette[i] for i in accent_is],
        "surface": _mix(palette[background_i], palette[text_i], 0.08),
        "muted": _mix(palette[text_i], palette[background_i], 0.45),
    }


def _parse_hex(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def _mix(a: str, b: str, t: float) -> str:
    ra, ga, ba = _parse_hex(a)
    rb, gb, bb = _parse_hex(b)
    r = round(ra * (1 - t) + rb * t)
    g = round(ga * (1 - t) + gb * t)
    bl = round(ba * (1 - t) + bb * t)
    return _hex((r, g, bl))
