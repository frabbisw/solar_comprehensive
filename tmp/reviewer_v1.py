"""
agents/reviewer_v1.py

STATUS: PRESERVED for backward compatibility with existing results.

This is the ORIGINAL reviewer (Exp 2 legacy) that used Solar's bias_info
and related_info. It contains a known bug:

  BUG: Solar's related_info lists attributes the code DID use, not what
  is MISSING. Passing it as "MISSING ATTRIBUTES" to the LLM is backwards —
  the LLM receives attributes already present in the code as if they were
  absent.

Preserved so you can reproduce the original Exp 2 results exactly.
For corrected behaviour, use agents/reviewer_v2.py.

Input files from Solar:
  bias_info<id>.jsonl    → {"bias_info": "gender,race"} or {"bias_info": "none"}
                           Meaning: sensitive attributes PRESENT in conditions (remove them)
  related_info<id>.jsonl → {"related_info": "income,gpa"} or {"related_info": "none"}
                           Solar meaning: related attributes the code used
                           Bug: treated here as "missing" attributes — incorrect

Writes: <output_dir>/task_<id>_review.jsonl
        {"review": "<instruction or 'pass'>"}
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import read_jsonl_list, task_code_path, task_review_path, append_jsonl


PROMPT_STYLES = {
    "gpt": {
        # Original prompt — kept unchanged to match old results
        "agent": (
            "You are a fairness-aware code reviewer. "
            "You are given a task prompt, the generated method, "
            "a list of BIASED attributes (sensitive attributes incorrectly used in conditions), "
            "and a list of MISSING attributes (required attributes absent from conditions). "
            "Write a concise repair instruction in plain English that tells the repairer "
            "exactly what to remove and what to add. "
            "If both lists are empty, respond with exactly: pass"
        ),
    }
}


class ReviewerV1Agent(BaseAgent):

    extra_args = [
        (["--code_dir"],         {"required": True}),
        (["--bias_info_dir"],    {"required": True, "help": "Solar bias_info directory"}),
        (["--related_info_dir"], {"required": True, "help": "Solar related_info directory"}),
        (["--output_dir"],       {"required": True}),
    ]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        style     = PROMPT_STYLES[args.model][args.prompt_style]
        code_path = task_code_path(args.code_dir, task_id)
        bias_path = os.path.join(args.bias_info_dir,    f"bias_info{task_id}.jsonl")
        rel_path  = os.path.join(args.related_info_dir, f"related_info{task_id}.jsonl")
        out_path  = task_review_path(args.output_dir, task_id)

        if not os.path.exists(code_path):
            print(f"  SKIP: missing code file {code_path}"); return
        if not os.path.exists(bias_path) or not os.path.exists(rel_path):
            print(f"  SKIP: missing Solar output for task {task_id}"); return

        code_lines = read_jsonl_list(code_path)
        bias_lines = read_jsonl_list(bias_path)
        rel_lines  = read_jsonl_list(rel_path)

        open(out_path, "w").close()
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        n = min(args.num_samples, len(code_lines), len(bias_lines), len(rel_lines))
        for i in range(n):
            bias_info    = bias_lines[i].get("bias_info",    "none")
            # BUG (preserved): related_info here is what Solar says the code USED,
            # but it is passed to the LLM as if it were "missing" attributes.
            related_info = rel_lines[i].get("related_info",  "none")

            if bias_info == "none" and related_info == "none":
                append_jsonl(out_path, {"review": "pass"})
                continue

            user_msg = (
                f"TASK PROMPT:\n{prompt}\n\n"
                f"GENERATED METHOD:\n{code_lines[i].get('generated_code', '')}\n\n"
                f"BIASED ATTRIBUTES (remove from conditions):\n"
                f"  {bias_info if bias_info != 'none' else 'none'}\n\n"
                f"MISSING ATTRIBUTES (add to conditions):\n"
                f"  {related_info if related_info != 'none' else 'none'}\n"
            )
            review = chat(style, user_msg, model=args.model, model_version=args.model_version,
                          temperature=args.temperature, max_tokens=256)
            append_jsonl(out_path, {"review": review.strip()})


if __name__ == "__main__":
    ReviewerV1Agent().run_cli()
