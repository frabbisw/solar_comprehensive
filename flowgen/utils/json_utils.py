#!/usr/bin/env python3
"""Small JSON helpers for FlowGen's LLM-facing legacy code.

The 2025 FlowGen hand-off assumed the model returned a bare JSON object.
Modern models sometimes add a short prefix/suffix or Markdown fences even when
asked for JSON.  These helpers recover the first valid JSON object without
changing the prompt semantics or the object contents.
"""
from __future__ import annotations

import json
from typing import Any


def parse_first_json_object(text: str) -> dict[str, Any]:
    """Return the first valid JSON object embedded in *text*.

    This accepts exact JSON as well as harmless leading/trailing prose or
    Markdown fences.  It never invents or repairs JSON fields.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("LLM response is empty; expected a JSON object")

    decoder = json.JSONDecoder()
    s = text.strip()

    # Fast path for a clean response.
    try:
        value = json.loads(s)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    # Robust path: try raw-decoding from every possible object start.  This
    # deliberately ignores only material outside the first valid JSON object.
    for pos, ch in enumerate(s):
        if ch != "{":
            continue
        try:
            value, _end = decoder.raw_decode(s[pos:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value

    raise ValueError("No valid JSON object found in LLM response")


def get_required_string(obj: dict[str, Any], key: str) -> str:
    """Read a required non-empty string field from a parsed JSON object."""
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"JSON field {key!r} is missing or empty")
    return value
