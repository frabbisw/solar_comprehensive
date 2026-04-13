"""
fma/bias_aware_requirements.py  —  Fairness Requirement Analyst

IN:  task prompt + existing functional PRD from agents/requirements.py
OUT: task_<id>_requirements.jsonl  {"PRD": "updated PRD with fairness constraints"}

Reads the functional PRD and updates it to remove any demographic bias —
ensuring the decision logic is based only on what the task explicitly requires.
Can run multiple rounds (--fma_req_rounds) where each round feeds the
previous round's PRD as input.

Round 1: reads from func_spec/
Round 2+: reads from previous fair_spec round output
"""
import sys, os

from typer import prompt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import extract_json_block, task_requirements_path, append_jsonl, read_jsonl_list

SYSTEM_PROMPT = (
    "You are a strict bias remover. You will be given a task and a PRD. "
    "read the task and correct the PRD by deleting any biased content towards anything not asked by the task. be very strict about removing any contents from the PRD, you will get reward for removing biases."
    "rewrite the bias free PRD an return."
    "Respond ONLY with JSON: {\"PRD\": \"<rewritten instruction>\"}"
)

class BiasAwareRequirementsAgent(BaseAgent):
    extra_args = [
        (["--output_dir"],  {"required": True}),
        (["--prd_dir"],     {"required": True,
                             "help": "Directory containing the input PRD (from requirements.py or previous round)"}),
    ]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        out_path = task_requirements_path(args.output_dir, task_id)
        prd_path = task_requirements_path(args.prd_dir, task_id)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        open(out_path, "w").close()

        # Read existing PRD
        prd = ""
        if os.path.exists(prd_path):
            lines = read_jsonl_list(prd_path)
            if lines and not lines[0].get("_parse_error"):
                prd = lines[0].get("PRD", "")

        user_msg = f"TASK:\n{prompt}\n\nEXISTING PRD:\n{prd}" if prd else f"TASK:\n{prompt}"
        # user_msg = f"TASK:\n{prompt}" if prd else f"TASK:\n{prompt}"

        for _ in range(args.num_samples):
            raw  = chat(SYSTEM_PROMPT, user_msg, model=args.model,
                        temperature=args.temperature, max_tokens=128)
            spec = extract_json_block(raw) or {"PRD": prd, "_parse_error": True}
            append_jsonl(out_path, spec)

if __name__ == "__main__":
    BiasAwareRequirementsAgent().run_cli()