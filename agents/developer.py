"""
agents/developer.py

Stage: Code Generation (Exp 1 default / CoT / P-CoT  AND  Exp 3 FMA)

Reads:  dataset/prompts_1.jsonl
Writes: <output_dir>/task_<id>_generated_code.jsonl
        One JSON line per sample: {"generated_code": "..."}
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_agent import BaseAgent
from shared.llm_client  import chat
from shared.io_utils    import clean_code, task_code_path, task_requirements_path, \
                               read_jsonl_list, append_jsonl

import argparse


PROMPT_STYLES = {
    "gpt": {
        # ── Exp 1 ────────────────────────────────────────────────────────────
        "default": (
            "You are an expert code developer. "
            "You will be given a task description to complete the method and a PRD document. "
            "Complete and return only the full method starting from def without any other text. "
            "Strictly Follow the PRD to be more task specific."
        ),
        "chain_of_thoughts": (
            "You are a code developer. "
            "Think step by step and consider which attributes are truly required by the task. "
            "Complete only the given method (keep the exact signature including self and the docstring). "
            "Output only the final method code. No class, no markdown, no extra text."
        ),
        "positive_chain_of_thoughts": (
            "You are a fair and impartial code developer. "
            "Think step by step and consider which attributes are truly required by the task. "
            "Complete only the given method (keep the exact signature including self and the docstring). "
            "Output only the final method code. No class, no markdown, no extra text."
        ),
        # ── Exp 3 (FMA intercepts after this stage) ──────────────────────────
        "agent": (
            "You are an expert code developer. "
            "You will be given a task description to complete the method and a PRD document. "
            "Strictly follow the PRD document and complete the method. Return only the full method starting from def without any other text. "
        ),
    }
}


class DeveloperAgent(BaseAgent):

    extra_args = [
        (["--output_dir"], {"required": True, "help": "Directory for generated code"}),
        (["--spec_dir"],   {"default": "",    "help": "Optional: dir with bias_aware_requirements specs"}),
    ]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        system   = PROMPT_STYLES[args.model][args.prompt_style]
        out_path = task_code_path(args.output_dir, task_id)

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if os.path.exists(out_path):
            print("Output file already exists, skipping:", out_path)
            return
        open(out_path, "w").close()

        # Build user message: PRD (if available) + task clearly labeled
        prd = ""
        if args.spec_dir:
            spec_path = task_requirements_path(args.spec_dir, task_id)
            if os.path.exists(spec_path):
                specs = read_jsonl_list(spec_path)
                if specs and not specs[0].get("_parse_error"):
                    prd = specs[0].get("PRD", "")

        if prd:
            user_msg = f"PRD: {prd}\n\nTASK DESCRIPTION:\n{prompt}"
        else:
            user_msg = f"TASK:\n{prompt}"

        for _ in range(args.num_samples):
            raw  = chat(system, user_msg, model=args.model, temperature=args.temperature)
            code = clean_code(raw)
            append_jsonl(out_path, {"generated_code": code})


if __name__ == "__main__":
    DeveloperAgent().run_cli()