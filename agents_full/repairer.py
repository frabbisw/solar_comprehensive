"""Functional Repairer for the post-Developer RQ4 FMA loop."""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils import (
    append_jsonl,
    clean_code,
    read_jsonl_list,
    task_code_path,
    task_requirements_path,
    task_review_path,
)

SYSTEM_PROMPT = (
    "You are the Functional Repairer. Fix only the functional fault reported for the GENERATED METHOD. "
    "Use the FUNCTIONAL PRD when it is available and valid, and use the TASK REFERENCE to determine which inputs "
    "actually exist. Preserve already-correct behavior and do not add unrelated decision factors. Never invent an "
    "attribute, field, threshold, domain rule, or external fact that is not supported by the supplied inputs. If the "
    "requested repair would require unavailable information or an unspecified business rule, preserve the current "
    "method instead of fabricating a solution. Preserve the method name/signature. Return only the complete Python "
    "method starting with def, with no markdown or explanation."
)


class RepairerAgent(BaseAgent):
    extra_args = [
        (["--code_dir"], {"required": True}),
        (["--review_dir"], {"required": True}),
        (["--spec_dir"], {"default": "", "help": "Functional PRD directory"}),
        (["--output_dir"], {"required": True}),
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

        prd = ""
        prd_invalid = False
        if args.spec_dir:
            p = task_requirements_path(args.spec_dir, task_id)
            if os.path.exists(p):
                rows = read_jsonl_list(p)
                if rows:
                    spec_row = rows[0]
                    prd = str(spec_row.get("PRD", "")).strip()
                    prd_invalid = bool(spec_row.get("_parse_error")) or not prd
                else:
                    prd_invalid = True
            else:
                prd_invalid = True

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

            if review.get("pass") is True and not review.get("issue"):
                append_jsonl(
                    out_path,
                    {
                        "generated_code": code,
                        "repaired": False,
                        "functional_review_passed": True,
                        "fma_converged": False,
                    },
                )
                continue

            # A malformed review is not a functional finding. Preserve the
            # candidate and force another round rather than repairing invented
            # feedback or allowing early convergence.
            if review.get("_parse_error"):
                append_jsonl(
                    out_path,
                    {
                        "generated_code": code,
                        "repaired": False,
                        "repair_attempted": False,
                        "functional_review_passed": False,
                        "functional_review_invalid": True,
                        "fma_converged": False,
                    },
                )
                continue

            issue = str(review.get("issue", "")).strip()
            if not issue:
                append_jsonl(
                    out_path,
                    {
                        "generated_code": code,
                        "repaired": False,
                        "repair_attempted": False,
                        "functional_review_passed": False,
                        "functional_review_invalid": True,
                        "fma_converged": False,
                    },
                )
                continue

            spec_text = (
                "FUNCTIONAL PRD STATUS: unavailable/invalid. Do not infer missing business rules."
                if prd_invalid
                else f"FUNCTIONAL PRD:\n{prd}"
            )
            user_msg = (
                f"TASK REFERENCE (use it to determine what inputs actually exist):\n{prompt}\n\n"
                f"{spec_text}\n\n"
                f"GENERATED METHOD:\n{code}\n\n"
                f"FUNCTIONAL FAULT TO REPAIR:\n{issue}"
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
                        "functional_repair_failed": True,
                        "functional_review_passed": False,
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
                        "functional_repair_failed": False,
                        # The repair itself has not yet been independently
                        # re-reviewed, so do not permit convergence this round.
                        "functional_review_passed": False,
                        "fma_converged": False,
                    },
                )


if __name__ == "__main__":
    RepairerAgent().run_cli()
