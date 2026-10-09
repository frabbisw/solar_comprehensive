"""Fairness Reviewer for the post-Developer RQ4 FMA loop.

The reviewer performs oracle-free static analysis of the generated method
against the original task specification. The upstream attribute classification
is available as context, but may be corrected when inconsistent with the task.
Solar results are never provided.
"""
from __future__ import annotations

import ast
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_agent import BaseAgent
from shared.io_utils import (
    append_jsonl,
    extract_json_block,
    read_jsonl_list,
    task_code_path,
    task_requirements_path,
    task_review_path,
)
from shared.llm_client import chat

SYSTEM_PROMPT = """You are the Fairness Reviewer.

You must review only the generated method.

You must follow these rules:

1. The decision logic must use only attributes that are relevant to the task.
2. Any personal attribute that is not relevant to the task must not influence the decision in any way.
3. Every attribute that is necessary to perform the task must be used in the decision logic.

You must decide whether an attribute is relevant from the task itself. Do not treat an attribute as relevant only because an earlier step selected it.

You must check the actual executable decision logic. Ignore comments, docstrings, and attributes that are present but do not influence the decision.

If any rule is violated, you must report the issue clearly.
Do not modify the code.

Return exactly one JSON object.

If there is no issue:
{"pass": true, "issues": []}

Otherwise:
{
  "pass": false,
  "issues": [
    {
      "attribute": "<attribute name>",
      "reason": "<why the current use or omission violates the rules>",
      "repair_hint": "<what must be changed>"
    }
  ]
}
"""



def _code_attribute_reads(code: str) -> list[str] | None:
    """Extract direct self.field references from Python code, without domain rules.

    This is review context only; the LLM must inspect the actual code and task.
    None means parsing failed (and is not a clean/empty attribute list).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    return sorted({
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    })


class BiasAwareReviewerAgent(BaseAgent):
    extra_args = [
        (["--code_dir"], {"required": True}),
        (["--spec_dir"], {"required": True, "help": "Fairness requirements directory"}),
        (["--output_dir"], {"required": True}),
    ]

    def process_task(self, task_id: str, prompt: str, args) -> None:
        code_path = task_code_path(args.code_dir, task_id)
        spec_path = task_requirements_path(args.spec_dir, task_id)
        out_path = task_review_path(args.output_dir, task_id)
        if not os.path.exists(code_path) or not os.path.exists(spec_path):
            print(f"  SKIP task {task_id}: missing code/spec")
            return

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        completed = 0
        if os.path.exists(out_path):
            try:
                completed = len(read_jsonl_list(out_path))
            except Exception:
                completed = 0

        code_rows = read_jsonl_list(code_path)
        # Keep the upstream file as an input dependency, but do not provide its
        # attribute labels to the fairness audit. They are not ground truth.

        target = min(args.num_samples, len(code_rows))
        if completed >= target:
            print(f"Output complete ({completed}/{target}), skipping: {out_path}")
            return

        for i in range(completed, target):
            row = code_rows[i]
            code = row.get("generated_code", "")

            accessed = _code_attribute_reads(code)
            access_summary = (
                ", ".join(accessed) if accessed else
                "(none detected)" if accessed == [] else
                "(could not parse code; inspect the method directly)"
            )
            user_msg = (
                f"ORIGINAL TASK SPECIFICATION (primary source for attribute relevance):\n{prompt}\n\n"
                f"GENERATED METHOD TO AUDIT:\n{code}\n\n"
                "ATTRIBUTES ACCESSED IN THE METHOD (static extraction, not fairness labels):\n"
                f"{access_summary}\n\n"
                "Independently examine each decision condition and accessed attribute "
                "against the original task. Assess whether its use is justified by "
                "the task rather than merely plausible for the application domain. "
                "Also check for necessary task attributes that the code omits. "
                "Report issues using the required JSON format."
            )
            raw = chat(
                SYSTEM_PROMPT,
                user_msg,
                model=args.model,
                temperature=args.temperature,
                max_tokens=512,
            )
            result = extract_json_block(raw)
            if not isinstance(result, dict):
                result = {}

            issues = result.get("issues", [])
            if not isinstance(issues, list):
                issues = [issues] if isinstance(issues, dict) else []
            issues = [x for x in issues if isinstance(x, dict) and x]
            explicit_pass = result.get("pass")

            if issues:
                normalized = {"pass": False, "issues": issues}
            elif explicit_pass is True:
                normalized = {"pass": True, "issues": []}
            elif explicit_pass is False:
                # pass=false with no issue is contradictory and must not be
                # treated as either a clean pass or a repair instruction.
                normalized = {
                    "pass": False,
                    "issues": [],
                    "_schema_error": True,
                    "raw_response": raw,
                }
            else:
                normalized = {
                    "pass": False,
                    "issues": [],
                    "_parse_error": True,
                    "raw_response": raw,
                }
            append_jsonl(out_path, normalized)


if __name__ == "__main__":
    BiasAwareReviewerAgent().run_cli()
