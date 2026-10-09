#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" Entrance of this project
"""
# !/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" Entrance of this project
"""
import os
import json
from utils.workflow import Workflow, return_root_absolute_path
import traceback

workflow_dir = os.path.join(return_root_absolute_path(), "workflow")


def main(prompt, flowPath=f"rawGPT/rawGPT.json"):
    # loads workflow
    task_id = prompt.get("task_id")
    if task_id is None:
        raise ValueError("Task ID is missing in the provided prompt.")
    workflow = Workflow()
    flow = workflow.loads_workflow(file_path=os.path.join(workflow_dir, flowPath))
    # run workflow
    workspace = workflow.create_workspace(task_id=task_id)

    for each_stage in flow:
        step_lists = each_stage["steps"]
        print(f"[*] Stage:{each_stage['stage']}")

        while len(step_lists) > 0:
            step = step_lists.pop(0)
            print(f"[*] Step:{step['key']}, Leader:{step['leader']}, Version:{step['key version']}")

            try:
                # Attempt to perform the step in the workflow
                workflow.do_step(step, step['leader'], workspace=workspace, task=prompt.get("prompt"), workflow=flowPath)
            except Exception as e:
                # Log the error and continue with the next step
                print(f"Error during step {step['key']} in stage {each_stage['stage']}: {str(e)}")
                # Optionally log the stack trace for debugging
                traceback.print_exc()

    try:
        # Attempt to load the final result from the log
        with open(os.path.join(workspace, "log.json"), "r") as f:
            result = json.load(f)["FinalCode"]
    except Exception as e:
        # Handle the case where the final code log might not exist or be incomplete
        print(f"Error loading final code from log: {str(e)}")
        result = None

    return result, workspace


def load_prompts_from_jsonl(file_path: str) -> list:
    """
    Reads all lines from a .jsonl file and returns a list of prompts.
    """
    prompts = []
    with open(file_path, 'r') as file:
        # Read each line, parse it as JSON, and extract the prompt
        for line in file:
            prompt_data = json.loads(line)
            # Assuming the prompt is stored under the key 'prompt'
            task_id = prompt_data.get("task_id")
            prompt = prompt_data.get("prompt", "")
            if task_id is not None:
                prompts.append({"task_id": task_id, "prompt": prompt})
    return prompts


if __name__ == "__main__":
    # Replace 'your_file_path.jsonl' with the path to your actual jsonl file
    prompt_file_path = "prompts_7.jsonl"

    # Load all prompts from the jsonl file
    test_prompts = load_prompts_from_jsonl(prompt_file_path)

    # Iterate through each prompt and run the main function
    for test_prompt in test_prompts:
        try:
            result, workspace = main(test_prompt, flowPath="waterfall_solar/waterfall_solar.json")
            # result, workspace = main(test_prompt, flowPath="rawGPT/rawGPT.json")
            # result, workspace = main(test_prompt, flowPath="scrum/scrum.json")
            print("test prompt", test_prompt)
            print(f"Final code: {result}\nWorkspace: {workspace}")
        except Exception as e:
            print(f"Error during processing prompt: {test_prompt}")
            # Optionally log the full stack trace for debugging
            traceback.print_exc()

# if __name__ == "__main__":
#     # Replace 'your_file_path.jsonl' with the path to your actual jsonl file
#     prompt_file_path = "prompts_70.jsonl"
#
#     # Load all prompts from the jsonl file
#     test_prompts = load_prompts_from_jsonl(prompt_file_path)
#
#     # Iterate through each prompt and run the main function
#     for test_prompt in test_prompts:
#         # print(main(test_prompt, flowPath="rawGPT/rawGPT.json"))
#         # You can uncomment other lines if needed for different flow paths
#         # print(main(test_prompt, flowPath="scrum/scrum.json"))
#         # print(main(test_prompt, flowPath="testdriven/testdriven.json"))
#         print(main(test_prompt, flowPath="waterfall/waterfall.json"))
