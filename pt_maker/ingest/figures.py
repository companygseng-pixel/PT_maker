"""Extract embedded figures from a PDF and attempt to pair them with captions.

Each figure is written to a caller-supplied output directory; caption text is
the nearest text block below the image bbox that starts with a figure keyword.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class FigureExtract:
    page: int
    index: int
    image_path: str
    bbox: tuple[float, float, float, float]
    caption: str = ""


_FIG_CAPTION_RE = re.compile(r"^\s*(fig(ure)?|figure|그림|도표)[\.\s\-:]*\d+",
                              re.IGNORECASE)


def extract_figures(
    pdf_path: str | Path,
    out_dir: str | Path,
    max_pages: int | None = None,
    min_area_in2: float = 0.8,
) -> list[FigureExtract]:
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[FigureExtract] = []
    doc = fitz.open(str(pdf_path))

    for pi, page in enumerate(doc):
        if max_pages and pi >= max_pages:
            break
        # Pull text blocks (for caption matching)
        text_blocks = page.get_text("blocks") or []

        for xi, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n >= 5:  # CMYK → RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                # Filter tiny images
                w_in = pix.width / 72.0
                h_in = pix.height / 72.0
                if w_in * h_in < min_area_in2:
                    pix = None
                    continue
                out_path = out_dir / f"p{pi + 1:03d}_fig{xi:02d}.png"
                pix.save(str(out_path))
                pix = None
            except Exception:
                continue

            # Find bbox on page (last occurrence)
            rects = page.get_image_rects(xref) or []
            bbox = tuple(rects[0]) if rects else (0.0, 0.0, 0.0, 0.0)

            # Caption = nearest text block below with fig prefix
            caption = ""
            if bbox and bbox[3] > 0:
                candidates = [b for b in text_blocks if b[1] > bbox[3] - 4]
                candidates.sort(key=lambda b: b[1])
                for b in candidates[:3]:
                    txt = (b[4] or "").strip()
                    if _FIG_CAPTION_RE.match(txt):
                        caption = txt.replace("\n", " ")
                        break

            results.append(FigureExtract(
                page=pi + 1, index=xi,
                image_path=str(out_path), bbox=bbox, caption=caption,
            ))
    doc.close()
    return results
