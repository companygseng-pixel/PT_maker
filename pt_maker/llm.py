"""Thin wrapper around the Anthropic SDK used by outline/drafter/reviewer.

Keeps all model + prompt-caching policy in one place so we can tune it.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

DEFAULT_MODEL = os.environ.get("PTMAKER_MODEL", "claude-opus-4-6")


def call_json(
    system: str,
    user: str,
    *,
    model: str | None = None,
    max_tokens: int = 4096,
    extra_system_cached: str | None = None,
) -> dict[str, Any]:
    """Call Claude with the convention that the response is JSON."""
    import anthropic

    client = anthropic.Anthropic()
    sys_blocks: list[dict[str, Any]] = []
    if extra_system_cached:
        sys_blocks.append({
            "type": "text",
            "text": extra_system_cached,
            "cache_control": {"type": "ephemeral"},
        })
    sys_blocks.append({"type": "text", "text": system})

    resp = client.messages.create(
        model=model or DEFAULT_MODEL,
        max_tokens=max_tokens,
        system=sys_blocks,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    return _extract_json(text)


def _extract_json(text: str) -> dict[str, Any]:
    """Tolerant JSON extractor — handles fenced code and trailing prose."""
    # Try fenced ```json ... ``` block first
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # Fall back to first brace-balanced object
    start = text.find("{")
    if start < 0:
        raise ValueError(f"No JSON object in LLM response:\n{text[:400]}")
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("Unbalanced braces in LLM response")
