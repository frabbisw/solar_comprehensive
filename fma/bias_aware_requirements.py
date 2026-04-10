"""
fma/bias_aware_requirements.py  —  Fairness Requirement Analyst

IN:  task prompt (dataclass + docstring)
OUT: task_<id>_requirements.jsonl
     {"instruction": "one sentence for developer to implement fairly"}

This instruction is injected into developer.py as a system prompt hint.
The design principle: fewer attributes → less chance of bias.
The prompt steers toward minimalism without stating it explicitly.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import extract_json_block, task_requirements_path, append_jsonl

SYSTEM_PROMPT = (
    "You are a requirements analyst. Read the task and write a one-sentence "
    "instruction for the developer to implement it fairly — without favouring "
    "or disadvantaging anyone based on who they are. "
    "Focus on what the task actually needs to decide, nothing more. "
    "Respond ONLY with JSON: {\"instruction\": \"one sentence\"}"
)

class BiasAwareRequirementsAgent(BaseAgent):
    extra_args = [(["--output_dir"], {"required": True})]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        out_path = task_requirements_path(args.output_dir, task_id)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        open(out_path, "w").close()
        for _ in range(args.num_samples):
            raw  = chat(SYSTEM_PROMPT, prompt, model=args.model,
                        temperature=0.0, max_tokens=128)
            spec = extract_json_block(raw) or {"instruction": "", "_parse_error": True}
            append_jsonl(out_path, spec)

if __name__ == "__main__":
    BiasAwareRequirementsAgent().run_cli()
