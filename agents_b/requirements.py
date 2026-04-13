"""
agents/requirements.py  —  Functional Requirement Engineer

IN:  task prompt (dataclass + docstring)
OUT: task_<id>_requirements.jsonl
     {"pass": true}                       if requirements are clear
     {"criterion": "one sentence"}        if something needed clarification
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import extract_json_block, task_requirements_path, append_jsonl

SYSTEM_PROMPT = (
    "You are a requirements analyst. Read the coding task carefully. "
    "If the task description is clear and complete, respond with: {\"pass\": true}\n"
    "If anything is ambiguous or missing, rewrite it as a clear one-sentence criterion. "
    "Respond ONLY with JSON: {\"pass\": true} or {\"criterion\": \"one sentence\"}"
)

class RequirementsAgent(BaseAgent):
    extra_args = [(["--output_dir"], {"required": True})]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        out_path = task_requirements_path(args.output_dir, task_id)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        open(out_path, "w").close()
        for _ in range(args.num_samples):
            raw  = chat(SYSTEM_PROMPT, prompt, model=args.model,
                        temperature=0.0, max_tokens=128)
            spec = extract_json_block(raw) or {"pass": True, "_parse_error": True}
            append_jsonl(out_path, spec)

if __name__ == "__main__":
    RequirementsAgent().run_cli()
