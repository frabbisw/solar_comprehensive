"""
agents/requirements.py  —  Functional Requirement Analyst

IN:  task prompt (dataclass + docstring)
OUT: task_<id>_requirements.jsonl  {"PRD": "one sentence describing the decision logic"}

Generates a functional PRD describing what the method should do and what
factors drive the decision. This is then passed to fma/bias_aware_requirements.py
which reviews and updates it for fairness.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import extract_json_block, task_requirements_path, append_jsonl

SYSTEM_PROMPT = (
    "You are a requirements analyst. You will be given a task description. "
    "Write a one-sentence PRD describing the decision logic. "
    "Be precise and specific about the conditions. focus on the task and ignore anything not explicitly required. "
    "Respond ONLY with JSON: {\"PRD\": \"<one sentence>\"}"
)

class RequirementsAgent(BaseAgent):
    extra_args = [(["--output_dir"], {"required": True})]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        out_path = task_requirements_path(args.output_dir, task_id)
        
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if os.path.exists(out_path):
            print("Output file already exists, skipping:", out_path)
            return
        open(out_path, "w").close()

        for _ in range(args.num_samples):
            raw  = chat(SYSTEM_PROMPT, prompt, model=args.model,
                        temperature=args.temperature, max_tokens=128)
            spec = extract_json_block(raw) or {"PRD": "", "_parse_error": True}
            append_jsonl(out_path, spec)

if __name__ == "__main__":
    RequirementsAgent().run_cli()