변환할 원본 문서(PDF 논문/보고서)를 여기에 넣어주세요.

## 지원 포맷
- `.pdf` — 현재 주 지원 포맷 (논문/IR 보고서/업무보고서)

## 사용 방법

```bash
# 전체 파이프라인 실행
python -m pt_maker.cli make-deck sources/내논문.pdf \
    --theme company \
    --purpose academic \
    --language ko \
    --slides 14

# 또는 단계별 실행
python -m pt_maker.cli ingest   sources/내논문.pdf --tables --figures
python -m pt_maker.cli outline  sources/내논문.pdf --purpose academic
python -m pt_maker.cli draft    --outline .ptmaker/outlines/내논문.json --theme company
python -m pt_maker.cli render   .ptmaker/slides/내논문.json
```

## 참고
- 이 폴더 내용은 `.gitignore` 로 제외됩니다 (기밀 문서 보호)
- 추출된 그림은 `.ptmaker/figures/<문서이름>/` 에 저장됩니다
