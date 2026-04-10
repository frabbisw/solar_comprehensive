"""
fma/bias_repairer.py  —  Fairness Code Repairer

IN:  task prompt + generated code + review {"pass":true} or
     {"issue": "attr_name", "reason": "..."}
OUT: task_<id>_generated_code.jsonl
     {"generated_code": "...", "repaired": true/false, "rounds": N}

Repair iterations up to --num_rounds (max 3, justified by ChatRepair/Reflexion).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import (clean_code, read_jsonl_list,
                                task_code_path, task_review_path, append_jsonl)

SYSTEM_PROMPT = (
    "You are a code developer. Rewrite the method to fix a fairness issue. "
    "Remove any condition that depends on the flagged attribute. "
    "The method should produce the same result for all people regardless of that attribute. "
    "Keep the EXACT method signature (including self) and the EXACT docstring. "
    "Output ONLY the fixed method code. No class, no markdown, no extra text."
)

class BiasRepairerAgent(BaseAgent):
    extra_args = [
        (["--code_dir"],   {"required": True}),
        (["--review_dir"], {"required": True}),
        (["--output_dir"], {"required": True}),
        (["--num_rounds"], {"type": int, "default": 1}),
    ]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        num_rounds  = min(args.num_rounds, 3)
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
                append_jsonl(out_path, {"generated_code": code, "repaired": False, "rounds": 0})
                continue

            current = code
            for _ in range(num_rounds):
                user_msg = (
                    f"TASK:\n{prompt}\n\n"
                    f"METHOD:\n{current}\n\n"
                    f"FAIRNESS ISSUE:\n"
                    f"  Attribute: {review.get('issue', '')}\n"
                    f"  Reason: {review.get('reason', '')}"
                )
                raw     = chat(SYSTEM_PROMPT, user_msg, model=args.model,
                               temperature=0.0, max_tokens=1024)
                current = clean_code(raw)

            append_jsonl(out_path, {"generated_code": current, "repaired": True, "rounds": num_rounds})

if __name__ == "__main__":
    BiasRepairerAgent().run_cli()
