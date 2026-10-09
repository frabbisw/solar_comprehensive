"""Functional Reviewer for the post-Developer RQ4 FMA loop.

The reviewer is fairness-unaware. It evaluates only the generated method against
the functional PRD. Solar and the fairness attribute classification are never
visible to this agent.
"""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils import (
    append_jsonl,
    extract_json_block,
    read_jsonl_list,
    task_code_path,
    task_requirements_path,
    task_review_path,
)

SYSTEM_PROMPT = (
    "You are the Functional Reviewer. Evaluate only the GENERATED METHOD for functional correctness. "
    "Use the FUNCTIONAL PRD when it is available and valid. The TASK REFERENCE is context only and may contain an "
    "intentionally incomplete target-method scaffold; never report syntax or completeness faults in that scaffold. "
    "Check the generated method's signature/structure, return behavior, conditions, thresholds/operators, and "
    "whether concrete PRD-required decision logic is implemented. Do not judge social fairness and do not invent new "
    "requirements, thresholds, domain rules, attributes, or data that are not supported by the supplied inputs. "
    "Never require the method to read an attribute or fact that is absent from the TASK REFERENCE. If a PRD branch "
    "depends on information that the task does not provide, do not ask the repairer to fabricate that information. "
    "If the FUNCTIONAL PRD is unavailable or invalid, use only explicit requirements in the TASK REFERENCE; when no "
    "concrete defect can be established from those inputs, pass the method rather than inventing criteria. "
    "Return exactly one JSON object: either {\"pass\":true,\"issue\":\"\"} or "
    "{\"pass\":false,\"issue\":\"one concise, actionable functional repair instruction grounded in the supplied inputs\"}."
)


class ReviewerAgent(BaseAgent):
    extra_args = [
        (["--code_dir"], {"required": True}),
        (["--spec_dir"], {"default": "", "help": "Functional PRD directory (fairness-unaware)"}),
        (["--output_dir"], {"required": True}),
    ]

    def process_task(self, task_id: str, prompt: str, args) -> None:
        code_path = task_code_path(args.code_dir, task_id)
        out_path = task_review_path(args.output_dir, task_id)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if not os.path.exists(code_path):
            print(f"  SKIP task {task_id}: missing code")
            return

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
        target = min(args.num_samples, len(code_rows))
        if completed >= target:
            print(f"Output complete ({completed}/{target}), skipping: {out_path}")
            return

        for i in range(completed, target):
            row = code_rows[i]
            code = row.get("generated_code", "")
            spec_text = (
                "FUNCTIONAL PRD STATUS: unavailable/invalid. Do not infer missing business rules.\n"
                if prd_invalid
                else f"FUNCTIONAL PRD:\n{prd}\n"
            )
            user_msg = (
                f"TASK REFERENCE (context only; use it to determine what inputs actually exist):\n{prompt}\n\n"
                f"{spec_text}\n"
                f"GENERATED METHOD TO REVIEW:\n{code}"
            )
            raw = chat(
                SYSTEM_PROMPT,
                user_msg,
                model=args.model,
                temperature=args.temperature,
                max_tokens=256,
            )
            result = extract_json_block(raw)
            issue = str(result.get("issue", "")).strip() if isinstance(result, dict) else ""
            passed = result.get("pass") if isinstance(result, dict) else None

            if passed is True and not issue:
                normalized = {"pass": True, "issue": ""}
            elif passed is False and issue:
                normalized = {"pass": False, "issue": issue}
            elif issue:
                # Accept a useful issue even if the model omitted the explicit
                # pass=false field, but make the normalization visible.
                normalized = {"pass": False, "issue": issue, "_schema_normalized": True}
            else:
                normalized = {
                    "pass": False,
                    "issue": "Reviewer output could not be parsed or did not match the required schema",
                    "_parse_error": True,
                    "raw_response": raw,
                }
            append_jsonl(out_path, normalized)


if __name__ == "__main__":
    ReviewerAgent().run_cli()
