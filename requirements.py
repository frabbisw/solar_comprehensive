"""
agents/requirements.py

Stage: Requirement Engineering  (used in multi-agent Exp 2 / FlowGen-style runs)

Reads:  dataset/prompts_1.jsonl
Writes: <output_dir>/task_<id>_requirements.jsonl
        One JSON line per sample:
        {"requirements": "<natural language requirement document>"}

Note: For Exp 1 (single-prompt), this agent is skipped.
      For Exp 3 (FMA), see fma/bias_aware_requirements.py instead.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse
from shared.base_agent  import BaseAgent
from shared.llm_client  import chat
from shared.io_utils    import task_requirements_path, append_jsonl


PROMPT_STYLES = {
    "gpt": {
        "agent": (
            "You are a software requirement engineer. "
            "Given a coding task description, write a concise requirement document "
            "that identifies: (1) the decision logic the function must implement, "
            "(2) which input attributes are relevant to that decision, "
            "and (3) which attributes are irrelevant and must not influence the outcome. "
            "Be specific and use the attribute names from the prompt. "
            "Respond in plain text, no markdown headers."
        ),
    }
}


class RequirementsAgent(BaseAgent):

    extra_args = [
        (["--output_dir"], {"required": True, "help": "Directory for requirements output"}),
    ]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        style    = PROMPT_STYLES[args.model][args.prompt_style]
        out_path = task_requirements_path(args.output_dir, task_id)

        open(out_path, "w").close()
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        for _ in range(args.num_samples):
            raw = chat(style, prompt, model=args.model,
                       temperature=args.temperature, max_tokens=512)
            append_jsonl(out_path, {"requirements": raw.strip()})


if __name__ == "__main__":
    RequirementsAgent().run_cli()
