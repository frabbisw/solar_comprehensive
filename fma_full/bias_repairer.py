"""Fairness Repairer for the post-Developer RQ4 FMA loop."""
from __future__ import annotations

import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_agent import BaseAgent
from shared.io_utils import (
    append_jsonl,
    clean_code,
    read_jsonl_list,
    task_code_path,
    task_requirements_path,
    task_review_path,
)
from shared.llm_client import chat

SYSTEM_PROMPT = """You are the Fairness Repairer.

You must repair the generated method according to all issues reported by the Fairness Reviewer.

You must follow these rules:

1. The decision logic must use only attributes that are relevant to the task.
2. You must remove the influence of any personal attribute that is not relevant to the task.
3. You must include any missing task-relevant attribute when the task provides enough information to use it correctly.
4. You must preserve all correct logic that is unrelated to the reported issues.
5. You must not invent new attributes, rules, thresholds, or decision criteria.
6. You must not change the method name or signature.

If the task does not provide enough information to make a requested change correctly, do not invent the missing information.

Return only the complete repaired Python method.
Do not include markdown or explanation.
"""



class BiasRepairerAgent(BaseAgent):
    extra_args = [
        (["--code_dir"], {"required": True}),
        (["--review_dir"], {"required": True}),
        (["--spec_dir"], {"default": "", "help": "Fairness requirements directory"}),
        (["--output_dir"], {"required": True}),
        (["--num_rounds"], {"type": int, "default": 1}),
    ]

    def process_task(self, task_id: str, prompt: str, args) -> None:
        code_path = task_code_path(args.code_dir, task_id)
        review_path = task_review_path(args.review_dir, task_id)
        out_path = task_code_path(args.output_dir, task_id)
        if not os.path.exists(code_path) or not os.path.exists(review_path):
            print(f"  SKIP task {task_id}: missing inputs")
            return

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        completed = 0
        if os.path.exists(out_path):
            try:
                completed = len(read_jsonl_list(out_path))
            except Exception:
                completed = 0

        spec = {}
        if args.spec_dir:
            p = task_requirements_path(args.spec_dir, task_id)
            if os.path.exists(p):
                rows = read_jsonl_list(p)
                if rows:
                    spec = rows[0]

        code_rows = read_jsonl_list(code_path)
        review_rows = read_jsonl_list(review_path)
        n = min(args.num_samples, len(code_rows), len(review_rows))
        if completed >= n:
            print(f"Output complete ({completed}/{n}), skipping: {out_path}")
            return

        for i in range(completed, n):
            code_row = code_rows[i]
            code = code_row.get("generated_code", "")
            review = review_rows[i]

            issues = review.get("issues", []) or []
            if review.get("pass") is True and not issues:
                append_jsonl(
                    out_path,
                    {
                        "generated_code": code,
                        "repaired": False,
                        "rounds": 0,
                        # A pass preserves code but does not suppress later reviews.
                        "fma_converged": False,
                        "fairness_review_passed": True,
                        "awaiting_functional_recheck": not bool(
                            code_row.get("functional_review_passed", False)
                        ),
                    },
                )
                continue

            if review.get("_parse_error") or review.get("_schema_error") or not issues:
                append_jsonl(
                    out_path,
                    {
                        "generated_code": code,
                        "repaired": False,
                        "repair_attempted": False,
                        "review_invalid": True,
                        "rounds": 0,
                        "fma_converged": False,
                    },
                )
                continue

            user_msg = (
                f"ORIGINAL TASK SPECIFICATION (primary source for attribute relevance):\n{prompt}\n\n"
                f"GENERATED METHOD:\n{code}\n\n"
                f"FAIRNESS FAULT REPORT (address the reported issues):\n"
                f"{json.dumps(issues, ensure_ascii=False)}"
            )
            raw = chat(
                SYSTEM_PROMPT,
                user_msg,
                model=args.model,
                temperature=args.temperature,
                max_tokens=768,
            )
            repaired = clean_code(raw)

            if repaired.strip() == "# NO CODE GENERATED":
                append_jsonl(
                    out_path,
                    {
                        "generated_code": code,
                        "repaired": False,
                        "repair_attempted": True,
                        "repair_parse_failed": True,
                        "rounds": 1,
                        "fma_converged": False,
                        "raw_response": raw,
                    },
                )
            else:
                append_jsonl(
                    out_path,
                    {
                        "generated_code": repaired,
                        "repaired": repaired != code,
                        "repair_attempted": True,
                        "repair_parse_failed": False,
                        "rounds": 1,
                        "fma_converged": False,
                    },
                )


if __name__ == "__main__":
    BiasRepairerAgent().run_cli()
