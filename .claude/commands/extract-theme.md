---
description: Extract a reusable theme from a reference design (PPTX/PDF/image) and save it under .ptmaker/themes/.
argument-hint: <reference_path> [name]
---

Use the `theme-extractor` subagent to process `$ARGUMENTS`.

Steps:
1. Parse `$ARGUMENTS` as `<path> [name]`.
2. Delegate to the theme-extractor agent with that path (and name if provided).
3. After the agent returns, print the theme path and the dominant colors.
4. Ask the user whether to proceed to `/make-deck` now.
