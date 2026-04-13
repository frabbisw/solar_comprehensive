"""
fma/bias_repairer.py  —  Fairness Code Repairer

IN:  task prompt + generated code + review {"pass":true} or {"issues": ["..."]}
OUT: task_<id>_generated_code.jsonl
     {"generated_code": "...", "repaired": true/false}

Multiple reviewer→repairer rounds are handled by the outer loop in run_pipeline.sh.
--num_rounds here is kept for compatibility but capped at 1.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import (clean_code, read_jsonl_list,
                                task_code_path, task_review_path, append_jsonl)

# SYSTEM_PROMPT = (
#     "You are an expert bias aware fair code repairer. You will be given a prompt, a generated method from the prompt, and an instruction from the reviewer to remove biases from the method. "
#     "Ignore the instruction if it introduces new biases or causes errors. "
#     "Keep the EXACT signature and docstring. Output ONLY the method starting from def."
# )

SYSTEM_PROMPT = (
    "You are an expert fair code repairer. You will be given a task description, a generated method from the task, and an instruction from the reviewer about problematic attributes. you have to remove them from influencing the method's outcome. "
    "Ignore the instruction if it causes errors or asks to add more attributes in the method. "
    "Keep the EXACT signature and docstring. Output ONLY the method starting from def."
)

class BiasRepairerAgent(BaseAgent):
    extra_args = [
        (["--code_dir"],   {"required": True}),
        (["--review_dir"], {"required": True}),
        (["--output_dir"], {"required": True}),
        (["--num_rounds"], {"type": int, "default": 1}),
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
        if os.path.exists(out_path):
            print("Output file already exists, skipping:", out_path)
            return
        open(out_path, "w").close()

        n = min(args.num_samples, len(code_lines), len(review_lines))
        for i in range(n):
            code   = code_lines[i].get("generated_code", "")
            review = review_lines[i]

            # Check pass — default to False so repair runs when "pass" key is absent
            has_issues = (
                bool(review.get("issues"))
                or bool(review.get("biases"))
                or bool(review.get("issue"))
            )
            is_pass = review.get("pass", not has_issues)

            if is_pass:
                append_jsonl(out_path, {"generated_code": code, "repaired": False, "rounds": 0})
                continue

            # Format issues — handle both list and string
            issues = review.get("issues") or review.get("biases") or review.get("issue") or ""
            if isinstance(issues, list):
                issues_str = "\n  ".join(issues)
            else:
                issues_str = str(issues)

            user_msg = (
                f"TASK DESCRIPTION:\n{prompt}\n\n"
                f"GENERATED METHOD:\n{code}\n\n"
                f"Instruction:\n  {issues_str}"
            )
            raw     = chat(SYSTEM_PROMPT, user_msg, model=args.model,
                           temperature=args.temperature, max_tokens=1024)
            current = clean_code(raw)

            append_jsonl(out_path, {"generated_code": current, "repaired": True, "rounds": 1})

if __name__ == "__main__":
    BiasRepairerAgent().run_cli()