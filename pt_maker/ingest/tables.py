"""Extract tables from a PDF using pdfplumber's heuristic line detector."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TableExtract:
    page: int
    rows: list[list[str]]
    bbox: tuple[float, float, float, float] | None = None
    caption: str = ""


def extract_tables(path: str | Path, max_pages: int | None = None) -> list[TableExtract]:
    try:
        import pdfplumber
    except ImportError:  # pragma: no cover
        return []

    path = Path(path)
    out: list[TableExtract] = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages):
            if max_pages and i >= max_pages:
                break
            try:
                tables = page.extract_tables() or []
            except Exception:
                tables = []
            for tbl in tables:
                # Clean: strip None → "" and trim whitespace
                cleaned = [
                    [(cell or "").strip() for cell in row]
                    for row in tbl
                    if any((cell or "").strip() for cell in row)
                ]
                if len(cleaned) >= 2 and len(cleaned[0]) >= 2:
                    out.append(TableExtract(page=i + 1, rows=cleaned))
    return out
