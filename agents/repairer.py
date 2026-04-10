"""
agents/repairer.py  —  Functional Code Repairer

IN:  task prompt + generated code + review {"pass":true} or {"issue":"..."}
OUT: task_<id>_generated_code.jsonl
     {"generated_code": "...", "repaired": true/false}
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import (clean_code, read_jsonl_list,
                                task_code_path, task_review_path, append_jsonl)

SYSTEM_PROMPT = (
    "You are a code developer. Fix the bug described in the issue. "
    "Keep the EXACT method signature (including self) and the EXACT docstring. "
    "Output ONLY the fixed method code. No class, no markdown, no extra text."
)

class RepairerAgent(BaseAgent):
    extra_args = [
        (["--code_dir"],   {"required": True}),
        (["--review_dir"], {"required": True}),
        (["--output_dir"], {"required": True}),
    ]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        code_path   = task_code_path(args.code_dir, task_id)
        review_path = task_review_path(args.review_dir, task_id)
        out_path    = task_code_path(args.output_dir, task_id)
        if not os.path.exists(code_path) or not os.path.exists(review_path):
            print(f"  SKIP task {task_id}: missing inputs"); return

        code_lines   = read_jsonl_list(code_path)
        review_lines = read_jsonl_list(review_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        open(out_path, "w").close()

        n = min(args.num_samples, len(code_lines), len(review_lines))
        for i in range(n):
            code   = code_lines[i].get("generated_code", "")
            review = review_lines[i]
            if review.get("pass", True):
                append_jsonl(out_path, {"generated_code": code, "repaired": False})
                continue
            user_msg = (
                f"TASK:\n{prompt}\n\n"
                f"METHOD:\n{code}\n\n"
                f"BUG:\n{review.get('issue', '')}"
            )
            raw = chat(SYSTEM_PROMPT, user_msg, model=args.model,
                       temperature=0.0, max_tokens=1024)
            append_jsonl(out_path, {"generated_code": clean_code(raw), "repaired": True})

if __name__ == "__main__":
    RepairerAgent().run_cli()
