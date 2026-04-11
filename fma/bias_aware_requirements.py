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
#     "You are a strict bias checker. You will be given a task description. "
#     "Write a one-sentence clear, bias related PRD instruction for the developer about the factors "
#     "the task explicitly requires, and bans all others from influencing the outcome."
#     "No assumptions, no social norms, no bias towards any group or individual. "
#     "Respond ONLY with JSON: {\"PRD\": \"<instruction>\"}"
# )

# SYSTEM_PROMPT = (
#     "You are a strict bias checker. You will be given a task description. "
#     "Write a one-line PRD identifying the required factors explicitly mentioned in the task, and ignore all other factors from influencing the outcome. "
#     # "no assumptions, no social norms, no bias towards any group or individual. "
#     "A factor is required ONLY if removing it would make the decision impossible. "
#     "Respond ONLY with JSON: {\"PRD\": \"<instruction>\"}"
# )

# SYSTEM_PROMPT = (
#     "You are a strict bias checker. You will be given a task description. "
#     "Write a one-sentence clear, bias related PRD instruction for the developer about the factors "
#     "the task explicitly requires, and bans all others from influencing the outcome."
#     "No assumptions, no social norms, no bias towards any group or individual. "
#     "Respond ONLY with JSON: {\"PRD\": \"<instruction>\"}"
# )

SYSTEM_PROMPT = (
    "You are a bias aware requirements generator. You will be given a task description. "
    "Write a strict PRD instruction for the developer to implement fair, bias-free code. "
    "Do not assume anything outside the task. "
    "You must be 100% confident, strict, and minimal about a factor to be included and allow it to influence the outcome. "
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