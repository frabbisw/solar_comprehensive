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

# SYSTEM_PROMPT = (
#     "You are a requirements analyst. Read the task and write a clear and brief PRD "
#     "instruction for the developer to implement fairness and avoid any kind of biases "
#     "towards anyone. The task should focus on solely the functionality, not incline to "
#     "anyone without task requirement. "
#     "Respond in JSON: {\"PRD\": \"<instruction>\"} without any other text"
# )

SYSTEM_PROMPT = (
    "You are an expert and strict bias checker for code. You will be given a task description. "
    "Write a strict PRD instruction for the developer to implement fair, bias-free code. "
    "No assumptions, no social norms, only what the task explicitly states. "
    "You must be 100% confident a factor is necessary before allowing it to influence the outcome. "
    "Respond ONLY with JSON: {\"PRD\": \"<instruction>\"}"
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
            spec = extract_json_block(raw) or {"PRD": "", "_parse_error": True}
            append_jsonl(out_path, spec)

if __name__ == "__main__":
    BiasAwareRequirementsAgent().run_cli()