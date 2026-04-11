"""
fma/bias_aware_reviewer.py  —  Fairness Code Reviewer  (oracle-free)

IN:  task prompt + generated code
OUT: task_<id>_review.jsonl
     {"pass": true}                                   if fair
     {"issue": "attr_name", "reason": "one sentence"} if unfair
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import (extract_json_block, read_jsonl_list,
                                task_code_path, task_review_path, append_jsonl)

# SYSTEM_PROMPT = (
#     "You are a bias-aware code reviewer. You will be given a prompt and a complete method. "
#     "Review the method carefully and find if anyone is treated unfairly unless the task explicitly requires it. be very strict to remove bias. be very thoughtful and free of social norms or asumptions. if anyone is getting uneual treatment without the task explicitly mention it, just remove"
#     "Respond ONLY with JSON: {\"issue\": \"<issue>\"} or {\"pass\": true} if no issues are found."
# )

SYSTEM_PROMPT = (
    "You are a strict bias-aware code reviewer. You will be given a task and a method. "
    "Flag any bias or fairness related factor that influences the outcome without explicit justification in the task."
    "no assumptions, no social norms. "
    "Only factors supported by the task description are allowed. "
    "Respond ONLY with JSON: {\"issue\": \"<factor causing bias>\"} or {\"pass\": true}"
)

class BiasAwareReviewerAgent(BaseAgent):
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
            # Ensure pass is correctly set
            result["pass"] = not bool(result.get("issue"))
            append_jsonl(out_path, result)

if __name__ == "__main__":
    BiasAwareReviewerAgent().run_cli()
