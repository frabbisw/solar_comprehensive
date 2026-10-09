"""Utilities for turning FlowGen's free-form LLM output into Solar-ready code.

FlowGen was originally run with GPT-3.5, which usually returned a bare method.
Newer models may wrap the method in Markdown or add prose before/after it.
Solar expects the JSONL ``generated_code`` field to contain executable Python
starting with the benchmark method definition.  These helpers normalize only
presentation; they do not change the generated method logic.
"""
from __future__ import annotations

import ast
import re
import textwrap


def expected_function_name(task_prompt: str) -> str | None:
    matches = re.findall(r"^\s*def\s+([A-Za-z_]\w*)\s*\(", task_prompt, flags=re.MULTILINE)
    return matches[-1] if matches else None


def _fenced_candidates(text: str) -> list[str]:
    blocks = re.findall(r"```(?:python|py)?\s*\n([\s\S]*?)```", text, flags=re.IGNORECASE)
    return [b.strip() for b in blocks if b.strip()]


def _extract_function_block(text: str, function_name: str | None) -> str | None:
    lines = text.splitlines()
    if function_name:
        pat = re.compile(rf"^(\s*)def\s+{re.escape(function_name)}\s*\(")
    else:
        pat = re.compile(r"^(\s*)def\s+[A-Za-z_]\w*\s*\(")

    starts: list[tuple[int, int]] = []
    for i, line in enumerate(lines):
        m = pat.match(line)
        if m:
            starts.append((i, len(m.group(1).expandtabs(4))))
    if not starts:
        return None

    # Prefer the last definition. FlowGen revision prompts sometimes echo an
    # original method and then provide the revised method afterward.
    start, base_indent = starts[-1]
    out = [lines[start]]
    saw_body = False
    for line in lines[start + 1 :]:
        if not line.strip():
            out.append(line)
            continue
        indent = len(line) - len(line.lstrip(" \t"))
        if indent <= base_indent and saw_body:
            break
        if indent > base_indent:
            saw_body = True
            out.append(line)
        elif not saw_body and line.lstrip().startswith(("#", "@")):
            out.append(line)
        else:
            break
    code = textwrap.dedent("\n".join(out)).strip()
    return code or None


def normalize_generated_code(raw_text: str, task_prompt: str) -> tuple[str | None, str | None]:
    """Return (Solar-ready method, error).

    The method logic is never rewritten.  We only strip prose/Markdown and
    isolate the final definition matching the task's method name.
    """
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return None, "empty model output"

    fn = expected_function_name(task_prompt)
    candidates = _fenced_candidates(raw_text)
    candidates.append(raw_text)

    # Search from the last fenced block backwards, then the whole response.
    for candidate in reversed(candidates):
        block = _extract_function_block(candidate, fn)
        if not block:
            continue
        try:
            tree = ast.parse(block)
        except SyntaxError:
            continue
        defs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if not defs:
            continue
        if fn and defs[0].name != fn:
            continue
        return block, None

    return None, f"could not isolate a syntactically valid definition for {fn or 'the benchmark method'}"
