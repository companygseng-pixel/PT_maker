---
description: Run the full PT_maker pipeline — ingest a PDF, generate outline, draft slides, review, and render a final PPTX.
argument-hint: <source.pdf> [--ref <design>] [--theme <name>] [--purpose academic|ir|business] [--slides N] [--language ko|en]
---

Your task is to build a high-quality deck from `$ARGUMENTS`.

## Plan

1. **Clarify** — if purpose, audience, language, or slide count isn't explicit in `$ARGUMENTS`, use AskUserQuestion to get them before doing anything heavy.
2. **Theme** — if `--theme` is given, reuse it. Else if `--ref` is given, delegate to `theme-extractor` first. Else warn the user and use the default theme.
3. **Outline** — delegate to `outline-writer` with the PDF + confirmed parameters.
4. **Draft** — delegate to `slide-drafter`.
5. **Review** — delegate to `deck-reviewer`.
6. **Deliver** — confirm the `.pptx` path, the QA warnings (if any), and ask the user whether to polish specific slides via `/edit-slide`.

## Quality bar

- Every data point traceable to a PDF page.
- WCAG AA contrast throughout.
- One message per slide.
- Korean + English glyphs both render correctly.
- Speaker notes present on every content slide.

Operate autonomously between stages unless a blocking issue surfaces.
