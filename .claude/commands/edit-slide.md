---
description: Edit one slide in an existing slides.json based on a natural-language request, then re-render.
argument-hint: <slides.json> <slide_id> "<request>"
---

Parse `$ARGUMENTS` as `<slides_path> <slide_id> <request>`.

1. Read the current slides.json.
2. Locate the slide with id == `<slide_id>`.
3. Apply the requested change minimally (preserve unrelated blocks).
4. Validate with `python -m pt_maker.cli review <slides_path> --qa-only` and address any new warnings.
5. Re-render: `python -m pt_maker.cli render <slides_path>`.
6. Show the diff summary and PPTX path.
