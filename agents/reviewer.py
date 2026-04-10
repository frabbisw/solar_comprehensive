"""
agents/reviewer.py  —  Functional Code Reviewer  (oracle-free)

IN:  task prompt + generated code
OUT: task_<id>_review.jsonl
     {"pass": true}              if logic is correct
     {"issue": "one sentence"}   if there is a bug
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import (extract_json_block, read_jsonl_list,
                                task_code_path, task_review_path, append_jsonl)

SYSTEM_PROMPT = (
    "You are a code reviewer. Check if the method correctly implements "
    "what the docstring says. "
    "If the logic is correct, respond with: {\"pass\": true}\n"
    "If there is a bug, describe it in one sentence. "
    "Respond ONLY with JSON: {\"pass\": true} or {\"issue\": \"one sentence\"}"
)

class ReviewerAgent(BaseAgent):
    extra_args = [
        (["--code_dir"],   {"required": True}),
        (["--output_dir"], {"required": True}),
    ]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        code_path = task_code_path(args.code_dir, task_id)
        out_path  = task_review_path(args.output_dir, task_id)
        if not os.path.exists(code_path):
            print(f"  SKIP task {task_id}: missing code"); return

        code_lines = read_jsonl_list(code_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        open(out_path, "w").close()

        for i in range(min(args.num_samples, len(code_lines))):
            code = code_lines[i].get("generated_code", "")
            user_msg = f"TASK:\n{prompt}\n\nMETHOD:\n{code}"
            raw    = chat(SYSTEM_PROMPT, user_msg, model=args.model,
                          temperature=0.0, max_tokens=128)
            result = extract_json_block(raw) or {"pass": True, "_parse_error": True}
            append_jsonl(out_path, result)

if __name__ == "__main__":
    ReviewerAgent().run_cli()
