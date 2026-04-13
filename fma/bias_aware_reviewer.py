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

# SYSTEM_PROMPT = (
#     "You are a strict bias-aware code reviewer. You will be given a task and a method. "
#     "Flag any factor that influences the outcome unless removing it would make the decision impossible. "
#     "No assumptions, no social norms, if in doubt, flag it. "
#     "Respond ONLY with JSON: {\"issue\": \"<factor causing bias>\"} or {\"pass\": true}"
# )

# SYSTEM_PROMPT = (
#     "You are a strict bias-aware code reviewer. You will be given a task and a method that is generated from the task by LLM."
#     "List all factors inside the method that should be removed to ensure fairness. if the task explicitly needs a factor, ignore it. "
#     "Do not presume any social norms or anything outside of the task. if you have doubt add it to the list to remove. "
#     "Respond ONLY with JSON. respond {\"issues\": [\"factor1\", \"factor2\"]}. "
# )
# if there is no biases, respond {\"pass\": true}

# SYSTEM_PROMPT = (
#     "You are a bias-aware code reviewer to ensure fairness. You will be given a task and a generated method from the task. "
#     "List all the factors influencing the outcome where the task does not explicitly require it. "
#     # "Ignore social norms and assumptions, judge only by what the task states. "
#     "if you have doubt about any factor, just add it to the list to remove. "
#     "Respond ONLY with JSON: {\"issues\": [\"factor1\", \"factor2\"]}. if there is no biases, just respond {\"pass\": true}"
# )

# SYSTEM_PROMPT = (
#     "You are a bias-aware code reviewer to ensure fairness. You will be given a prompt and a generated method from the prompt. "
#     "Review the method code and srictly look for any biases need to be removed. Find the factors that influence the outcome of the method but the task does not explicitly needs them. "
#     "Do not add any new factors, just work on existing bias factors to remove."
#     "Write a 1 line review document for the repairer who will fix the method by removing biases. Respond ONLY with JSON: {\"issues\": [\"<instructions>\"]}"
#     "return {\"pass\": true} if the the code is already fair. "
# )

# SYSTEM_PROMPT = (
#     "You are a bias-aware code reviewer. You will be given a task and a generated method. "
#     "Find factors in the method that influence the outcome but are not explicitly required by the task. "
#     "Only flag factors already in the code, do not suggest additions. "
#     "Respond ONLY with JSON: {\"issues\": \"instructions\"} just return {\"pass\": true} if it is fair."
# )

SYSTEM_PROMPT = (
    "You are a fair code reviewer. You will be given a task description and a generated method from the task. "
    "Write a 1 line feedback about which logics should be removed from the generated method to make it fair. any logic that is not explicitly required by the task should be removed. "
    "think solely on the task, do not get biased towards any group or individual, do not add any new logic, just remove the existing ones that cause bias. "
    "biased logics are those that cause unequal treatment to different groups or individuals without being explicitly required by the task. "
    "Respond ONLY with JSON: {\"issues\": \"instructions\"} just return {\"pass\": true} if it is fair."
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
        if os.path.exists(out_path):
            print("Output file already exists, skipping:", out_path)
            return
        open(out_path, "w").close()

        for i in range(min(args.num_samples, len(code_lines))):
            code = code_lines[i].get("generated_code", "")
            user_msg = f"TASK DESCRIPTION:\n{prompt}\n\nGENERATED METHOD:\n{code}"
            raw    = chat(SYSTEM_PROMPT, user_msg, model=args.model,
                          temperature=args.temperature, max_tokens=128)
            result = extract_json_block(raw) or {"pass": True, "_parse_error": True}
            # Ensure pass is correctly set
            # result["pass"] = not bool(result.get("issue"))
            result["pass"] = (
                not bool(result.get("issues"))
                and not bool(result.get("biases"))
                and not bool(result.get("issue"))
            )
            append_jsonl(out_path, result)

if __name__ == "__main__":
    BiasAwareReviewerAgent().run_cli()
