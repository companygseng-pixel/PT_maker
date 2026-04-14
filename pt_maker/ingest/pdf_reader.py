"""Read a PDF into a structured representation suitable for LLM consumption.

We use PyMuPDF for text and layout; the per-page block list preserves order
and position. Headings are heuristically detected by font size outliers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF


@dataclass
class TextBlock:
    page: int           # 1-indexed
    bbox: tuple[float, float, float, float]
    text: str
    avg_size: float
    is_heading: bool = False


@dataclass
class DocumentIngest:
    path: str
    title: str = ""
    pages: int = 0
    full_text: str = ""
    blocks: list[TextBlock] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def sections(self) -> list[tuple[str, str]]:
        """Split full_text into (heading, body) sections using detected headings."""
        sections: list[tuple[str, list[str]]] = [("(intro)", [])]
        for blk in self.blocks:
            if blk.is_heading:
                sections.append((blk.text.strip(), []))
            else:
                sections[-1][1].append(blk.text)
        return [(h, "\n".join(body).strip()) for h, body in sections if body or h != "(intro)"]


_HEADING_RE = re.compile(r"^(abstract|introduction|method(ology)?|result(s)?|discussion|"
                          r"conclusion(s)?|references|요약|서론|방법|결과|논의|결론|참고문헌)\b",
                          re.IGNORECASE)


def ingest_pdf(path: str | Path, max_pages: int | None = None) -> DocumentIngest:
    path = Path(path)
    doc = fitz.open(str(path))
    ing = DocumentIngest(path=str(path.resolve()), pages=len(doc))
    ing.meta = doc.metadata or {}
    ing.title = (ing.meta.get("title") or path.stem).strip() or path.stem

    full_text_parts: list[str] = []
    # Gather size stats first
    sizes: list[float] = []
    for page_i, page in enumerate(doc):
        if max_pages and page_i >= max_pages:
            break
        d = page.get_text("dict")
        for b in d.get("blocks", []):
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    sz = float(span.get("size", 0))
                    if sz > 0:
                        sizes.append(sz)

    body_size = _median(sizes) if sizes else 10.0
    heading_threshold = body_size * 1.2

    for page_i, page in enumerate(doc):
        if max_pages and page_i >= max_pages:
            break
        d = page.get_text("dict")
        for b in d.get("blocks", []):
            if b.get("type", 0) != 0:
                continue
            texts: list[str] = []
            span_sizes: list[float] = []
            bbox = b.get("bbox", (0, 0, 0, 0))
            for line in b.get("lines", []):
                line_txt = "".join(span.get("text", "") for span in line.get("spans", []))
                if line_txt.strip():
                    texts.append(line_txt)
                for span in line.get("spans", []):
                    sz = float(span.get("size", 0))
                    if sz > 0:
                        span_sizes.append(sz)
            text = "\n".join(texts).strip()
            if not text:
                continue
            avg = sum(span_sizes) / len(span_sizes) if span_sizes else body_size
            is_heading = (avg >= heading_threshold and len(text) < 140) or bool(
                _HEADING_RE.match(text.strip())
            )
            ing.blocks.append(TextBlock(
                page=page_i + 1, bbox=tuple(bbox), text=text,
                avg_size=avg, is_heading=is_heading,
            ))
            full_text_parts.append(text)

    ing.full_text = "\n\n".join(full_text_parts)
    doc.close()
    return ing


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    if n % 2:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2
