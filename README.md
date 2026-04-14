# PT_maker

Claude-powered high-quality PPTX generator for **academic presentations, IR
decks, and business reports**.

Feed it a reference design (PPTX/PDF/image) and a source document (PDF paper
or report) — PT_maker extracts the visual identity, drafts a deck, reviews
itself, and renders a polished `.pptx`.

## Features

- **Theme extraction** — pulls colors, typography, and placeholder layouts
  from PPTX (direct XML parse) or PDF/image (k-means palette + Claude Vision).
- **3-stage pipeline with review loop** — Outline → Draft → Self-critique →
  Render. Bounded at 2 review iterations to cap cost.
- **Native components** — real PPTX charts (bar/column/line/pie/scatter),
  styled tables, LaTeX math (matplotlib mathtext), Lucide icons, Mermaid /
  Graphviz diagrams.
- **Korean-first** — dual `latin`/`eastAsia` typeface slots so English and
  Korean glyphs each pick the right font. Pretendard + Noto Sans KR friendly.
- **Automated QA** — WCAG AA contrast, text overflow estimation, numeric
  traceability (every number must appear in the source), font availability.
- **Claude Code integration** — slash commands + subagents for interactive
  use, or a standalone CLI for scripting.

## Install

```bash
pip install -e .
# Optional for diagram rendering
npm install -g @mermaid-js/mermaid-cli
# Optional: system Graphviz
```

Set `ANTHROPIC_API_KEY` for the LLM-driven stages. Rule-based fallbacks run
without a key (lower quality).

## Quick start (CLI)

```bash
# 1. Extract a theme from a reference PPTX
python -m pt_maker.cli extract-theme design.pptx --name acme

# 2. Build the deck end-to-end
python -m pt_maker.cli make-deck paper.pdf \
    --theme acme --purpose academic --language ko --slides 14
```

The pipeline writes intermediate artifacts under `.ptmaker/` (themes, outlines,
slides, figures) so you can iterate without re-running expensive steps.

## Claude Code usage

From inside a Claude Code session in this repo:

```
/extract-theme design.pptx acme
/make-deck paper.pdf --theme acme --purpose academic --language ko
/polish-deck .ptmaker/slides/paper.json
/edit-slide .ptmaker/slides/paper.json s5 "put the main KPI chart here instead"
```

Each command delegates to a dedicated subagent (`theme-extractor`,
`outline-writer`, `slide-drafter`, `deck-reviewer`) so that long-running
Claude work happens in isolated context windows.

## Pipeline

```
   Reference ─────────────────────┐
 (pptx/pdf/img)                   ▼
                           theme_extractor ─► theme.json
   Source PDF
       │
       ▼
  pdf_reader + tables + figures
       │
       ▼
  outline_writer ─► outline.json
       │
       ▼
  slide_drafter  ─► slides.json (with theme)
       │
       ▼
  deck_reviewer (≤2 passes) ─► slides.json'
       │
       ▼
  render.engine ─► deck.pptx
```

## Directory map

```
pt_maker/
  theme/       from_pptx.py · from_pdf.py · from_image.py · palette.py · schema.py
  ingest/      pdf_reader.py · tables.py · figures.py
  outline/     generator.py · schema.py
  slides/      drafter.py · reviewer.py · schema.py
  components/  text · chart · table · math · icon · diagram · image · shape
  render/      engine.py · fonts.py
  qa/          checks.py
  cli.py · llm.py
.claude/
  agents/      theme-extractor · outline-writer · slide-drafter · deck-reviewer
  commands/    extract-theme · make-deck · polish-deck · add-slide · edit-slide
```

## Quality guarantees

The reviewer + QA layer enforces:

1. **One message per slide** — bullets split past 6 items or 80 chars.
2. **Numeric traceability** — every `\d+(\.\d+)?%?` token in text blocks
   must appear in the source PDF; otherwise a warning is raised.
3. **WCAG AA** — foreground/background contrast ≥ 4.5:1.
4. **Font availability** — `fc-list` check; missing fonts trigger a warning
   with a suggested fallback.
5. **Overflow estimation** — Pillow computes text box fit at the chosen point
   size.

## License

MIT.
