"""Standalone smoke test: render a demo deck from the default theme.

Run: ``python examples/demo_preview.py``
Output: ``demo.pptx`` in the current directory.
"""

from __future__ import annotations

from pt_maker.render.engine import render_deck
from pt_maker.slides.drafter import draft_slides_rule
from pt_maker.theme.schema import default_theme


OUTLINE = {
    "meta": {"title": "PT_maker 데모", "purpose": "ir", "language": "ko",
              "audience": "투자자", "duration_min": 10},
    "slides": [
        {"id": "s1", "type": "title",
         "title": "PT_maker",
         "subtitle": "Claude 기반 고품질 PPTX 자동 생성"},
        {"id": "s2", "type": "agenda", "title": "목차",
         "items": ["문제 정의", "접근 방법", "성과", "로드맵"]},
        {"id": "s3", "type": "section", "title": "1. 문제 정의"},
        {"id": "s4", "type": "content", "title": "왜 지금 PT 자동화인가",
         "bullets": [
             "보고서 작성 시간 평균 4.2시간/건",
             "디자인 가이드 준수율 38%",
             "데이터 재입력 오류율 6%",
         ],
         "notes": "실제 기업 40곳 설문 결과. 지표는 2024 Q3 기준."},
        {"id": "s5", "type": "chart", "title": "분기별 사용자 증가",
         "chart": {"kind": "line",
                   "data": {"categories": ["Q1", "Q2", "Q3", "Q4"],
                            "series": [{"name": "MAU (천)",
                                        "values": [12, 28, 54, 91]}]}}},
        {"id": "s6", "type": "table", "title": "경쟁사 비교",
         "headers": ["제품", "디자인 추출", "한글 지원", "수식"],
         "rows": [
             ["A사", "없음", "△", "X"],
             ["B사", "색상만", "O", "X"],
             ["PT_maker", "풀 추출", "O", "O"],
         ]},
        {"id": "s7", "type": "closing",
         "title": "감사합니다", "subtitle": "pt-maker@example.com"},
    ],
}


if __name__ == "__main__":
    theme = default_theme("demo")
    spec = draft_slides_rule(OUTLINE, theme)
    render_deck(spec, theme, "demo.pptx")
    print("wrote demo.pptx")
