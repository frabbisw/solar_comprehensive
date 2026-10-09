"""Fairness Requirements Analyst for the revised RQ4 FMA pipeline.

Input
-----
- original task specification
- functional PRD from agents_full/requirements.py

Output
------
JSONL record with:
- PRD: fairness-aware PRD passed to the Developer
- required_attributes: attributes judged explicitly needed by the task
- restricted_attributes: all other attributes (closed-world assumption)

The agent does not receive Solar results or benchmark labels.  Attribute names
are parsed from the task's class definition only so the agent can classify every
available factor without dataset-specific configuration.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_agent import BaseAgent
from shared.io_utils import (
    append_jsonl,
    extract_json_block,
    read_jsonl_list,
    task_requirements_path,
)
from shared.llm_client import chat

SYSTEM_PROMPT = (
    "You are the Fairness Requirements Analyst in a code-generation pipeline. "
    "You will receive a task, its available class attributes, and a functional PRD. "
    "Classify every available attribute using ONLY the task specification. "
    "Required attributes are factors that the task explicitly needs for the decision logic. "
    "Restricted attributes are all remaining factors. Use a closed-world assumption: "
    "if an attribute is not explicitly needed by the task, classify it as restricted. "
    "Do not justify an attribute using social norms, stereotypes, or real-world correlations. "
    "Rewrite the PRD so the required attributes drive the decision and restricted attributes "
    "must not influence the outcome. "
    "Respond ONLY with JSON: "
    '{"PRD":"...","required_attributes":["..."],"restricted_attributes":["..."]}'
)

_FIELD_RE = re.compile(r"^\s{4}([A-Za-z_]\w*)\s*:\s*[^=\n]+", re.MULTILINE)


def extract_attributes(prompt: str) -> list[str]:
    """Extract dataclass fields appearing before the target method."""
    prefix = prompt.split("\n    def ", 1)[0]
    seen: list[str] = []
    for name in _FIELD_RE.findall(prefix):
        if name not in seen:
            seen.append(name)
    return seen


class BiasAwareRequirementsAgent(BaseAgent):
    extra_args = [
        (["--output_dir"], {"required": True}),
        (["--prd_dir"], {"required": True, "help": "Functional PRD directory"}),
    ]

    def process_task(self, task_id: str, prompt: str, args) -> None:
        out_path = task_requirements_path(args.output_dir, task_id)
        prd_path = task_requirements_path(args.prd_dir, task_id)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        completed = 0
        if os.path.exists(out_path):
            try:
                completed = len(read_jsonl_list(out_path))
            except Exception:
                completed = 0
        if completed >= args.num_samples:
            print(f"Output complete ({completed}/{args.num_samples}), skipping: {out_path}")
            return

        functional_prd = ""
        if os.path.exists(prd_path):
            rows = read_jsonl_list(prd_path)
            if rows and not rows[0].get("_parse_error"):
                functional_prd = str(rows[0].get("PRD", ""))

        attributes = extract_attributes(prompt)
        user_msg = (
            f"TASK SPECIFICATION:\n{prompt}\n\n"
            f"AVAILABLE ATTRIBUTES:\n{attributes}\n\n"
            f"FUNCTIONAL PRD:\n{functional_prd}"
        )

        for _ in range(completed, args.num_samples):
            raw = chat(
                SYSTEM_PROMPT,
                user_msg,
                model=args.model,
                temperature=args.temperature,
                max_tokens=512,
            )
            obj = extract_json_block(raw)

            required_raw = obj.get("required_attributes", []) if isinstance(obj, dict) else []
            restricted_raw = obj.get("restricted_attributes", []) if isinstance(obj, dict) else []
            if not isinstance(required_raw, list):
                required_raw = []
            if not isinstance(restricted_raw, list):
                restricted_raw = []

            attr_set = set(attributes)
            required = [a for a in required_raw if isinstance(a, str) and a in attr_set]
            required = list(dict.fromkeys(required))
            required_set = set(required)

            # Closed-world enforcement is deterministic: anything not accepted
            # as explicitly required becomes restricted, regardless of whether
            # the model omitted it from its restricted list.
            restricted = [a for a in attributes if a not in required_set]

            prd = str(obj.get("PRD", "")).strip() if isinstance(obj, dict) else ""
            parse_error = not bool(obj)
            if not prd:
                prd = functional_prd.strip()
            classification = (
                f" Required attributes: {', '.join(required) if required else 'none explicitly identified'}."
                f" Restricted attributes: {', '.join(restricted) if restricted else 'none'}."
                " Only required attributes may influence the decision outcome."
            )
            if classification.strip() not in prd:
                prd = (prd.rstrip() + classification).strip()

            append_jsonl(
                out_path,
                {
                    "PRD": prd,
                    "required_attributes": required,
                    "restricted_attributes": restricted,
                    "available_attributes": attributes,
                    "closed_world": True,
                    "_parse_error": parse_error,
                },
            )


if __name__ == "__main__":
    BiasAwareRequirementsAgent().run_cli()
