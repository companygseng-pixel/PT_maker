---
description: Append a new slide to an existing slides.json via natural-language request.
argument-hint: <slides.json> "<natural-language description>"
---

Parse `$ARGUMENTS` as `<slides_path> <request>`.

1. Read the current slides.json.
2. Read the associated theme.json (from `theme_ref.name`).
3. Draft ONE new slide (choose a layout + blocks, keeping color tokens).
4. Append the new slide with a fresh `id` and save the file.
5. Re-render: `python -m pt_maker.cli render <slides_path>`.
6. Show the user the new slide's title and PPTX path.
