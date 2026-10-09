"""
shared/io_utils.py

Common I/O helpers used by all agents.
"""

import ast
import json
import os
import re
import textwrap
from typing import Iterator


# ---------------------------------------------------------------------------
# JSONL readers / writers
# ---------------------------------------------------------------------------

def read_jsonl(path: str) -> Iterator[dict]:
    """Yield parsed JSON objects from a JSONL file, skipping blank lines."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_jsonl_list(path: str) -> list:
    return list(read_jsonl(path))


def write_jsonl(path: str, records: list[dict]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            json.dump(rec, f, ensure_ascii=False)
            f.write("\n")


def append_jsonl(path: str, record: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
        f.write("\n")


# ---------------------------------------------------------------------------
# Code cleaning
# ---------------------------------------------------------------------------

def clean_code(text: str) -> str:
    """Normalize an LLM response to one standalone Python method.

    Repair models may return fenced code, surrounding prose, or a method with a
    multiline docstring whose interior lines do not follow normal indentation.
    Use Python's parser to find a complete function rather than slicing by
    indentation alone.
    """
    if not text:
        return "# NO CODE GENERATED"

    blocks = re.findall(r"```(?:python|py)?\s*\n([\s\S]*?)```", text, flags=re.IGNORECASE)
    candidates = list(blocks) + [text]

    for candidate in reversed(candidates):
        lines = candidate.splitlines()
        starts = [
            i for i, line in enumerate(lines)
            if re.match(r"^\s*(?:async\s+)?def\s+[A-Za-z_]\w*\s*\(", line)
        ]
        for start in reversed(starts):
            # Try the longest suffix first, trimming only trailing material until
            # Python accepts one complete function definition.
            for end in range(len(lines), start, -1):
                snippet = textwrap.dedent("\n".join(lines[start:end])).strip()
                if not snippet:
                    continue
                try:
                    tree = ast.parse(snippet)
                except SyntaxError:
                    continue

                funcs = [
                    node for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                if not funcs:
                    continue

                fn = funcs[0]
                code = ast.get_source_segment(snippet, fn) or snippet
                code = textwrap.dedent(code).strip()
                try:
                    compile(code, "<generated_method>", "exec")
                    return code
                except SyntaxError:
                    continue

    return "# NO CODE GENERATED"


def extract_json_block(text: str) -> dict:
    """Parse one JSON object from a model response.

    Prefer a bare JSON object, but defensively accept a fenced object or one
    surrounded by short prose. Return an empty dict when no object is parseable.
    """
    if not text:
        return {}

    cleaned = re.sub(r"```(?:json)?", "", text.strip(), flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").strip()
    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for i, ch in enumerate(cleaned):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(cleaned[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return {}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def task_code_path(base_dir: str, task_id: str) -> str:
    return os.path.join(base_dir, f"task_{task_id}_generated_code.jsonl")


def task_review_path(base_dir: str, task_id: str) -> str:
    return os.path.join(base_dir, f"task_{task_id}_review.jsonl")


def task_requirements_path(base_dir: str, task_id: str) -> str:
    return os.path.join(base_dir, f"task_{task_id}_requirements.jsonl")
