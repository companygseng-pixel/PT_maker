---
description: Run the reviewer + QA loop on an existing slides.json and re-render.
argument-hint: <slides.json> [--iterations 2]
---

Delegate to the `deck-reviewer` subagent with `$ARGUMENTS`.

After the agent returns, print the remaining QA warnings and the path to the updated PPTX.
