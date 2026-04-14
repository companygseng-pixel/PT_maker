"""Document → :class:`DeckOutline` via Claude."""

from __future__ import annotations

from typing import Any

from ..ingest.figures import FigureExtract
from ..ingest.pdf_reader import DocumentIngest
from ..ingest.tables import TableExtract
from ..llm import call_json

_SYSTEM = """\
You are a senior presentation writer producing deck outlines for \
academic, IR, or business audiences. Your outlines are crisp, logically \
ordered, and respect the original document's data. You NEVER invent \
numbers — every figure must be traceable to the source document via \
`source_page`. Respond with JSON only, matching the requested schema."""


def _purpose_guide(purpose: str, language: str) -> str:
    if purpose == "academic":
        ko = ("학술 발표 구조: 제목 → 연구 배경/동기 → 연구 질문 → 방법 → "
              "핵심 결과(그래프 위주) → 논의 → 한계 → 결론 → 참고문헌. "
              "수식은 꼭 필요할 때만, 결과는 숫자 인용을 유지.")
        en = ("Academic structure: Title → Background → Research Question → "
              "Method → Results (charts-heavy) → Discussion → Limitations → "
              "Conclusion → References. Preserve numeric citations exactly.")
        return ko if language == "ko" else en
    if purpose == "ir":
        ko = ("IR 구조: 표지 → Executive Summary → 시장 기회 → 제품/전략 → "
              "핵심 KPI(차트) → 재무(표) → 로드맵 → 팀 → 리스크/Q&A. "
              "숫자·통화·증감률은 원문 그대로.")
        en = ("IR structure: Cover → Executive Summary → Market → Product/"
              "Strategy → KPIs (charts) → Financials (table) → Roadmap → Team → "
              "Risk/Q&A. Keep numbers/currency/percent exactly as source.")
        return ko if language == "ko" else en
    # business
    ko = ("업무보고 구조: 표지 → 목적 → 현황 요약 → 주요 이슈 → 데이터(차트/표) → "
          "대안 비교 → 권고안 → 실행 계획 → 리스크. 슬라이드당 한 메시지 원칙.")
    en = ("Business report: Cover → Purpose → Status → Key Issues → Data → "
          "Options → Recommendation → Plan → Risks. One message per slide.")
    return ko if language == "ko" else en


def _summarize_ingest(
    ingest: DocumentIngest,
    tables: list[TableExtract],
    figures: list[FigureExtract],
    char_budget: int = 40_000,
) -> str:
    parts: list[str] = []
    parts.append(f"# Document: {ingest.title}")
    parts.append(f"Pages: {ingest.pages}\n")

    # Sectioned body
    for heading, body in ingest.sections():
        parts.append(f"## {heading}")
        parts.append(body)
        parts.append("")

    if tables:
        parts.append("## Tables extracted")
        for i, t in enumerate(tables):
            preview = " | ".join(t.rows[0][:6]) if t.rows else ""
            parts.append(f"- table_{i} (page {t.page}, {len(t.rows)} rows): {preview}")
        parts.append("")

    if figures:
        parts.append("## Figures extracted")
        for f in figures:
            parts.append(f"- {f.image_path} (page {f.page}): {f.caption}")

    text = "\n".join(parts)
    if len(text) > char_budget:
        text = text[:char_budget] + "\n…[truncated]"
    return text


def generate_outline(
    ingest: DocumentIngest,
    tables: list[TableExtract],
    figures: list[FigureExtract],
    *,
    purpose: str = "business",
    language: str = "ko",
    audience: str = "",
    duration_min: int = 15,
    target_slides: int = 12,
) -> dict[str, Any]:
    guide = _purpose_guide(purpose, language)
    source_summary = _summarize_ingest(ingest, tables, figures)

    user = f"""\
Produce a deck outline JSON for the following document.

Purpose: {purpose}
Language: {language}
Audience: {audience or "(unspecified)"}
Duration: ~{duration_min} minutes
Target slide count: {target_slides} (±2)

Structural guidance:
{guide}

Rules:
- Slide count must be within target ±2.
- Every slide with numbers must include `source_page` (1-indexed).
- `type` must be one of: title, agenda, section, content, chart, table, figure, equation, diagram, quote, closing.
- For type=chart, include `chart.kind` (bar|column|line|pie|scatter), `chart.data.categories`, `chart.data.series[]`.
- For type=table, include `rows` (2D array) and optional `headers`.
- For type=figure, include `image_ref` matching a figure path from the source.
- For type=equation, include `latex` (plain math, no $..$).
- For type=diagram, include `syntax` (mermaid|graphviz) and `code`.
- Speaker notes in `notes`, 2–4 sentences, in the same language.

Return JSON matching this schema:
{{
  "meta": {{"title": "...", "subtitle": "...", "authors": [...], "date": "...",
            "purpose": "{purpose}", "audience": "...", "duration_min": {duration_min},
            "language": "{language}", "source_pdf": "{ingest.path}"}},
  "slides": [ {{"id": "s1", "type": "...", ...}} ]
}}

=== SOURCE DOCUMENT ===
{source_summary}
=== END ===
"""

    return call_json(system=_SYSTEM, user=user, max_tokens=8192)
