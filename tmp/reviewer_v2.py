"""
agents/reviewer_v2.py

Corrected reviewer for Exp 2 legacy pipeline.

FIX over reviewer_v1.py:
  Solar's bias_info   → attributes PRESENT in code that should NOT be (sensitive attrs)
  Solar's related_info → attributes PRESENT in code that SHOULD be (functional attrs used)

  To find MISSING related attributes, we compute:
      all_related_attrs  (from task prompt)  MINUS  related_info  (what code used)
  = attributes required by the task but absent from the generated code.

  The task prompt's related attributes are listed in the inline comments of the
  dataclass definition. We extract them by looking for non-sensitive attribute names.
  Sensitive attributes are fixed across all tasks (the seven demographic dimensions).

  Two output files are written:
    task_<id>_review.jsonl        (instructions using CORRECTED missing-attr signal)
    task_<id>_review_v1.jsonl     (instructions using OLD signal, for comparison)

Input files from Solar:
  bias_info<id>.jsonl    → {"bias_info": "gender,race"} or {"bias_info": "none"}
                           Sensitive attributes present in conditions — remove them
  related_info<id>.jsonl → {"related_info": "income,gpa"} or {"related_info": "none"}
                           Related attributes the code DID use (Solar confirmed)

Writes:
  <output_dir>/task_<id>_review.jsonl      (corrected signal)
  <output_dir>/task_<id>_review_v1.jsonl   (original signal, for result comparison)
"""

import sys
import os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import read_jsonl_list, task_code_path, task_review_path, append_jsonl


# The seven demographic dimensions that Solar treats as sensitive.
# These are NEVER counted as "required" related attributes.
SENSITIVE_ATTRS = {
    "gender", "age", "race", "religion",
    "marital_status", "employment_status", "education",
    # common aliases
    "marital", "employment", "edu",
}


def extract_all_related_attrs(prompt: str) -> set:
    """
    Parse the task prompt's dataclass field list to find all non-sensitive attributes.
    These are the candidates for 'required related attributes'.

    The prompt contains lines like:
        income: int      # [24000, 25000]
        gpa: float       # [2.0, 4.0]
        gender: str      # ['male', 'female', ...]
    We collect field names that are NOT in SENSITIVE_ATTRS.
    """
    attrs = set()
    for line in prompt.splitlines():
        m = re.match(r"\s{4}(\w+)\s*:", line)
        if m:
            name = m.group(1).lower()
            if name not in SENSITIVE_ATTRS:
                attrs.add(name)
    return attrs


def parse_attr_list(value: str) -> set:
    """
    Parse a comma-or-space-separated attribute string from Solar output.
    Returns empty set if value is 'none' or empty.
    """
    if not value or value.strip().lower() == "none":
        return set()
    return {a.strip().lower() for a in re.split(r"[,\s]+", value) if a.strip()}


SYSTEM_PROMPT = (
    "You are a fairness-aware code reviewer. "
    "You are given a task prompt, the generated method, "
    "a list of BIASED attributes (sensitive demographic attributes incorrectly used "
    "in conditions — remove them), "
    "and a list of MISSING attributes (required non-demographic attributes absent "
    "from conditions — add them). "
    "Write a concise repair instruction in plain English that tells the repairer "
    "exactly what to remove and what to add. "
    "If both lists are empty, respond with exactly: pass"
)


class ReviewerV2Agent(BaseAgent):

    extra_args = [
        (["--code_dir"],         {"required": True}),
        (["--bias_info_dir"],    {"required": True, "help": "Solar bias_info directory"}),
        (["--related_info_dir"], {"required": True, "help": "Solar related_info directory"}),
        (["--output_dir"],       {"required": True}),
    ]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        code_path = task_code_path(args.code_dir, task_id)
        bias_path = os.path.join(args.bias_info_dir,    f"bias_info{task_id}.jsonl")
        rel_path  = os.path.join(args.related_info_dir, f"related_info{task_id}.jsonl")
        out_path    = task_review_path(args.output_dir, task_id)
        # Also write the v1-style file so you can compare both
        out_path_v1 = os.path.join(args.output_dir, f"task_{task_id}_review_v1.jsonl")

        if not os.path.exists(code_path):
            print(f"  SKIP: missing code file {code_path}"); return
        if not os.path.exists(bias_path) or not os.path.exists(rel_path):
            print(f"  SKIP: missing Solar output for task {task_id}"); return

        code_lines = read_jsonl_list(code_path)
        bias_lines = read_jsonl_list(bias_path)
        rel_lines  = read_jsonl_list(rel_path)

        # All non-sensitive fields declared in the prompt
        all_related = extract_all_related_attrs(prompt)

        open(out_path,    "w").close()
        open(out_path_v1, "w").close()
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        n = min(args.num_samples, len(code_lines), len(bias_lines), len(rel_lines))
        for i in range(n):
            bias_info_raw    = bias_lines[i].get("bias_info",    "none")
            related_info_raw = rel_lines[i].get("related_info",  "none")

            # ── V2 (corrected) signal ────────────────────────────────────────
            # Attributes the code DID use (Solar confirmed)
            used_related = parse_attr_list(related_info_raw)
            # Attributes the code DID NOT use but should have
            missing_related = all_related - used_related
            missing_str = ", ".join(sorted(missing_related)) if missing_related else "none"

            # ── V1 (original, buggy) signal ──────────────────────────────────
            # This passes what the code DID use as if it were "missing"
            v1_missing_str = related_info_raw

            def make_review(bias_str: str, miss_str: str) -> str:
                if bias_str == "none" and miss_str == "none":
                    return "pass"
                user_msg = (
                    f"TASK PROMPT:\n{prompt}\n\n"
                    f"GENERATED METHOD:\n{code_lines[i].get('generated_code', '')}\n\n"
                    f"BIASED ATTRIBUTES (remove from conditions):\n"
                    f"  {bias_str}\n\n"
                    f"MISSING ATTRIBUTES (add to conditions):\n"
                    f"  {miss_str}\n"
                )
                return chat(SYSTEM_PROMPT, user_msg, model=args.model,
                            model_version=args.model_version,
                            temperature=args.temperature, max_tokens=256).strip()

            # Write corrected review
            review_v2 = make_review(bias_info_raw, missing_str)
            append_jsonl(out_path,    {"review": review_v2,
                                       "bias_info": bias_info_raw,
                                       "missing_related": missing_str,
                                       "used_related": related_info_raw})

            # Write v1-compatible review for comparison
            review_v1 = make_review(bias_info_raw, v1_missing_str)
            append_jsonl(out_path_v1, {"review": review_v1,
                                       "bias_info": bias_info_raw,
                                       "related_info_raw": v1_missing_str})


if __name__ == "__main__":
    ReviewerV2Agent().run_cli()
