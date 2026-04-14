"""Self-critique loop — Claude reads the draft spec and returns an edit list.

Kept cheap: only critique, only request patches to slides that need them.
Bounded at 2 iterations to avoid runaway cost.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from ..llm import call_json

_SYSTEM = """\
You are an experienced presentation editor. You receive a draft slides spec \
and must return a JSON object with {"patches": [...], "comments": [...]}.
Each patch has {"slide_id": "s3", "replace_blocks": [...]} or \
{"slide_id": "s3", "update_notes": "..."}.
Only patch slides that truly need improvement (typos, overflow risk, unclear \
message, weak title, data mismatch). Respond with JSON only."""


def review_once(spec: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(spec, ensure_ascii=False)
    user = f"""\
Review this slides spec. Prioritize:
- Narrative flow across slides
- One-message-per-slide principle
- Title clarity & parallelism
- Over-packed bullets (split if > 6 items or > 80 chars)
- Missing speaker notes on data slides
- Korean/English mix: enforce consistent language per slide

Return JSON:
{{ "patches": [ {{"slide_id": "sX", "replace_blocks": [...], "update_notes": "..."}} ],
  "comments": [ "overall comment strings" ] }}

SPEC:
{payload}
"""
    return call_json(system=_SYSTEM, user=user, max_tokens=6000)


def apply_patches(spec: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(spec)
    by_id = {s["id"]: s for s in out.get("slides", [])}
    for patch in review.get("patches", []):
        sid = patch.get("slide_id")
        if sid not in by_id:
            continue
        if "replace_blocks" in patch and isinstance(patch["replace_blocks"], list):
            by_id[sid]["blocks"] = patch["replace_blocks"]
        if "update_notes" in patch and isinstance(patch["update_notes"], str):
            by_id[sid]["notes"] = patch["update_notes"]
    return out


def review_loop(spec: dict[str, Any], max_iterations: int = 2) -> dict[str, Any]:
    current = spec
    for _ in range(max_iterations):
        try:
            review = review_once(current)
        except Exception:
            break
        if not review.get("patches"):
            break
        current = apply_patches(current, review)
    return current
