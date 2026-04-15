디자인 레퍼런스 파일을 여기에 넣어주세요.

## 지원 포맷
- `.pptx` — 가장 정확한 추출 (마스터 레이아웃 · 색상 · 폰트 · 플레이스홀더 좌표)
- `.pdf`  — 표지 1페이지를 렌더링해서 색상/타이포 추론 (Claude Vision 사용)
- `.png`, `.jpg`, `.jpeg`, `.webp` — 단일 이미지 기반 추론

## 사용 방법

```bash
# 레퍼런스에서 테마 추출
python -m pt_maker.cli extract-theme references/회사템플릿.pptx --name company

# 추출된 테마로 덱 생성
python -m pt_maker.cli make-deck sources/논문.pdf --theme company --purpose academic
```

## 권장 네이밍
- 기관/회사별로 파일명 구분: `company_ir_2026.pptx`, `univ_paper_template.pptx`
- 한 파일에 한 테마만 (여러 테마 섞여있으면 추출 품질 저하)

## 참고
- 이 폴더 내용은 `.gitignore` 로 제외됩니다 (저작권 있는 템플릿 보호)
- 추출된 테마 JSON은 `.ptmaker/themes/<이름>.json` 에 저장됩니다
