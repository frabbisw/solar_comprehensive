"""
agents/reviewer.py

Stage: Functional Code Reviewer  (Normal agents pipeline)

Checks that the generated code uses the attributes that the task
logically requires, using Solar's output as the signal.

Generic design (no dataset-specific knowledge hardcoded):
  Solar's related_info tells us which fields the code currently uses.
  We compute "unused" = all_fields - overconditioned - conditioned.
  The LLM then decides which of those unused fields the task actually needs,
  by reasoning from the docstring — not from a hardcoded list.

Output:
  task_<id>_review.jsonl      corrected signal (v2)
  task_<id>_review_v1.jsonl   original buggy signal (v1) for comparison

Signal semantics:
  bias_info    → attrs that caused Solar test failures (overconditioned)
  related_info → attrs the code uses in conditions (conditioned)
  unused       = all_fields - overconditioned - conditioned

Reads:
  <code_dir>/task_<id>_generated_code.jsonl
  <bias_info_dir>/bias_info<id>.jsonl
  <related_info_dir>/related_info<id>.jsonl

Writes:
  <output_dir>/task_<id>_review.jsonl
  <output_dir>/task_<id>_review_v1.jsonl
"""

import sys
import os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import read_jsonl_list, task_code_path, task_review_path, append_jsonl


def extract_all_fields(prompt: str) -> set:
    """Extract all dataclass field names from the task prompt."""
    fields = set()
    for line in prompt.splitlines():
        m = re.match(r"    (\w+)\s*:", line)
        if m:
            fields.add(m.group(1).lower())
    return fields


def parse_solar_list(value: str) -> set:
    if not value or value.strip().lower() in ("none", ""):
        return set()
    return {a.strip().lower() for a in re.split(r"[,;\s]+", value) if a.strip()}


SYSTEM_PROMPT = (
    "You are a code reviewer. "
    "The generated method has access to several attributes but may not be using "
    "all of the ones the task logically requires. "
    "You are given the task description, the current method, and a list of "
    "UNUSED attributes (attributes available in the class but absent from conditions). "
    "Decide which of these unused attributes the task actually needs based on the "
    "docstring, then write a concise repair instruction telling the developer "
    "what to add and why. "
    "If no additions are needed, respond with exactly: pass"
)


class ReviewerAgent(BaseAgent):

    extra_args = [
        (["--code_dir"],          {"required": True}),
        (["--bias_info_dir"],     {"required": True,
                                   "help": "Solar test-failure attribute files"}),
        (["--related_info_dir"],  {"required": True,
                                   "help": "Solar used-attribute files (different dir from bias_info_dir)"}),
        (["--output_dir"],        {"required": True}),
    ]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        code_path = task_code_path(args.code_dir, task_id)
        bias_path = os.path.join(args.bias_info_dir,    f"bias_info{task_id}.jsonl")
        rel_path  = os.path.join(args.related_info_dir, f"related_info{task_id}.jsonl")
        out_path    = task_review_path(args.output_dir, task_id)
        out_path_v1 = os.path.join(args.output_dir, f"task_{task_id}_review_v1.jsonl")

        if not os.path.exists(code_path):
            print(f"  SKIP task {task_id}: missing code file"); return
        if not os.path.exists(bias_path):
            print(f"  SKIP task {task_id}: missing {bias_path}"); return
        if not os.path.exists(rel_path):
            print(f"  SKIP task {task_id}: missing {rel_path}"); return

        code_lines = read_jsonl_list(code_path)
        bias_lines = read_jsonl_list(bias_path)
        rel_lines  = read_jsonl_list(rel_path)
        all_fields = extract_all_fields(prompt)

        open(out_path,    "w").close()
        open(out_path_v1, "w").close()
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        n = min(args.num_samples, len(code_lines), len(bias_lines), len(rel_lines))
        for i in range(n):
            code     = code_lines[i].get("generated_code", "")
            bias_raw = bias_lines[i].get("bias_info",    "none")
            rel_raw  = rel_lines[i].get("related_info",  "none")

            overconditioned = parse_solar_list(bias_raw)
            conditioned     = parse_solar_list(rel_raw)
            # Fields the code doesn't use AND aren't causing failures
            unused = sorted(all_fields - overconditioned - conditioned)
            unused_str = ", ".join(unused) if unused else "none"

            # ── V2 corrected ────────────────────────────────────────────────
            if unused_str == "none":
                append_jsonl(out_path, {
                    "review": "pass", "unused": "none",
                    "conditioned": sorted(conditioned),
                })
            else:
                user_msg = (
                    f"TASK:\n{prompt}\n\n"
                    f"CURRENT METHOD:\n{code}\n\n"
                    f"UNUSED ATTRIBUTES (available in class, absent from conditions):\n"
                    f"  {unused_str}\n"
                )
                review = chat(SYSTEM_PROMPT, user_msg, model=args.model,
                              model_version=args.model_version,
                              temperature=args.temperature, max_tokens=256)
                append_jsonl(out_path, {
                    "review": review.strip(),
                    "unused": unused_str,
                    "conditioned": sorted(conditioned),
                })

            # ── V1 original bug (related_info passed as "missing") ───────────
            if rel_raw == "none":
                append_jsonl(out_path_v1, {"review": "pass", "related_info_raw": "none"})
            else:
                user_msg_v1 = (
                    f"TASK:\n{prompt}\n\n"
                    f"CURRENT METHOD:\n{code}\n\n"
                    f"MISSING ATTRIBUTES:\n  {rel_raw}\n"
                )
                review_v1 = chat(SYSTEM_PROMPT, user_msg_v1, model=args.model,
                                 model_version=args.model_version,
                                 temperature=args.temperature, max_tokens=256)
                append_jsonl(out_path_v1, {
                    "review": review_v1.strip(), "related_info_raw": rel_raw,
                })


if __name__ == "__main__":
    ReviewerAgent().run_cli()
