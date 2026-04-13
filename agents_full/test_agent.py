"""
agents/test_agent.py

Stage: Test Agent  (Normal agents pipeline — optional role)

Generates natural-language test descriptions that verify whether the
method treats all people consistently when only non-decision attributes
vary. Generic: no dataset-specific attribute names hardcoded.

Reads:  <code_dir>/task_<id>_generated_code.jsonl
Writes: <output_dir>/task_<id>_tests.jsonl
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import read_jsonl_list, task_code_path, append_jsonl


SYSTEM_PROMPT = (
    "You are a software tester. Given a coding task and a generated method, "
    "write 2-3 test cases in plain English. Each test should describe two "
    "people who are identical except for one attribute that should NOT affect "
    "the outcome, and assert they receive the same result. "
    "Base your tests only on the task description — do not assume which "
    "attributes are or are not decision-relevant. "
    "Format each test as: TEST: <description>"
)


class TestAgent(BaseAgent):

    extra_args = [
        (["--code_dir"],   {"required": True}),
        (["--output_dir"], {"required": True}),
    ]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        code_path = task_code_path(args.code_dir, task_id)
        out_path  = os.path.join(args.output_dir, f"task_{task_id}_tests.jsonl")

        if not os.path.exists(code_path):
            print(f"  SKIP task {task_id}: missing code file"); return

        code_lines = read_jsonl_list(code_path)
        
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if os.path.exists(out_path):
            print("Output file already exists, skipping:", out_path)
            return
        open(out_path, "w").close()

        for i in range(min(args.num_samples, len(code_lines))):
            code     = code_lines[i].get("generated_code", "")
            user_msg = f"TASK:\n{prompt}\n\nMETHOD:\n{code}\n"
            tests    = chat(SYSTEM_PROMPT, user_msg, model=args.model,
                            temperature=args.temperature, max_tokens=256)
            append_jsonl(out_path, {"tests": tests.strip()})


if __name__ == "__main__":
    TestAgent().run_cli()
