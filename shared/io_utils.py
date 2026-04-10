"""
shared/io_utils.py

Common I/O helpers used by all agents.
"""

import json
import os
import re
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
    """
    Normalise LLM code output to a plain method body string:
      - strip markdown fences
      - trim to start from 'def '
      - strip leading/trailing whitespace
    """
    if not text:
        return "# NO CODE GENERATED"
    # Remove fenced blocks
    text = text.replace("```python", "").replace("```", "").strip()
    if "def " not in text:
        return "# NO CODE GENERATED"
    if not text.startswith("def "):
        text = text[text.find("def "):]
    return text.strip()


def extract_json_block(text: str) -> dict:
    """
    Robustly parse a JSON object from an LLM response.
    Strips markdown fences before parsing.
    Returns an empty dict on failure (caller decides how to handle).
    """
    text = text.strip()
    text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
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
