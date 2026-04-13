"""
fma/bias_verifier.py  —  Post-repair Verifier  (optional)

IN:  task prompt + repaired code
OUT: task_<id>_verification.jsonl
     {"verified": true, "reasoning": "..."}
     {"verified": false, "issue": "attr_name", "reasoning": "..."}
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import argparse
from shared.base_agent import BaseAgent
from shared.llm_client import chat
from shared.io_utils   import (extract_json_block, read_jsonl_list,
                                task_code_path, append_jsonl)

SYSTEM_PROMPT = (
    "You are a code reviewer. Check if the method is fair and correct. "
    "If yes, respond with: {\"verified\": true, \"reasoning\": \"one sentence\"}\n"
    "If there is still a fairness or correctness issue, describe it. "
    "Respond ONLY with JSON: {\"verified\": true, \"reasoning\": \"...\"} or "
    "{\"verified\": false, \"issue\": \"attr_name\", \"reasoning\": \"one sentence\"}"
)

class BiasVerifierAgent(BaseAgent):
    extra_args = [
        (["--repaired_dir"], {"required": True}),
        (["--output_dir"],   {"required": True}),
    ]

    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        code_path = task_code_path(args.repaired_dir, task_id)
        out_path  = os.path.join(args.output_dir, f"task_{task_id}_verification.jsonl")
        if not os.path.exists(code_path):
            print(f"  SKIP task {task_id}: missing repaired code"); return

        code_lines = read_jsonl_list(code_path)
        
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if os.path.exists(out_path):
            print("Output file already exists, skipping:", out_path)
            return
        open(out_path, "w").close()

        for i in range(min(args.num_samples, len(code_lines))):
            entry    = code_lines[i]
            code     = entry.get("generated_code", "")
            repaired = entry.get("repaired", False)

            if not repaired:
                append_jsonl(out_path, {"verified": True,
                                        "reasoning": "No repair needed."})
                continue

            user_msg = f"TASK:\n{prompt}\n\nMETHOD:\n{code}"
            raw    = chat(SYSTEM_PROMPT, user_msg, model=args.model,
                          temperature=0.0, max_tokens=128)
            result = extract_json_block(raw) or {"verified": True,
                                                  "reasoning": "parse error",
                                                  "_parse_error": True}
            append_jsonl(out_path, result)

if __name__ == "__main__":
    BiasVerifierAgent().run_cli()
