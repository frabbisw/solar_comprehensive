#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util
"""
import os
import json
import re
import shutil
import subprocess

from utils.keys.unified_llm_api import UnifiedLLMAPI
from utils.keys.base_key import BaseKey
from utils.json_utils import parse_first_json_object, get_required_string


def get_bias_info_from_jsonl(file_path, variant_number):
    """
    Extracts the bias_info for the given variant number from a JSONL file.

    :param file_path: Path to the JSONL file.
    :param variant_number: The variant number to search for.
    :return: The bias_info for the given variant number, or None if not found.
    """
    with open(file_path, 'r') as file:
        for line in file:
            data = json.loads(line.strip())
            if data.get("variant") == str(variant_number):
                return data.get("bias_info")
    return None


class BUGFIX_TEST_Iteration(BaseKey):
    version_map = {
        "0.0.1": "unify_bugfix_test_iteration",
    }

    def _repair_code(self, workspace, code_version):
        llm_api = UnifiedLLMAPI()
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_repair_code.json")
        original_code = self._get_information_from_log(workspace, f"Code{code_version}")
        test_report = self._get_information_from_log(workspace, f"TestReport{code_version}")
        prompt["Context"] = f"# the original code:\n{original_code}\n# test report:\n{test_report}"
        prompt["Question"] += self._get_raw_question(workspace)
        prompt = json.dumps(prompt)

        code_set = set()
        for j in range(code_version + 1):
            code_set.add(self._get_information_from_log(workspace, f"Code{j}"))

        # Modern models sometimes wrap otherwise-valid JSON or decide that the
        # current code already needs no change. Retry those cases, but do not
        # convert a usable code artifact into a fatal workflow error.
        statuses = []
        for attempt in range(3):
            raw = llm_api.execute("default_json_prompt", prompt=prompt)["content"]
            self._write_log(workspace, f"RepairResponse{code_version + 1}", raw, prompt=prompt)
            try:
                obj = parse_first_json_object(raw)
                revised = get_required_string(obj, "revised_code")
            except ValueError as exc:
                statuses.append({"attempt": attempt + 1, "status": "parse_error", "detail": str(exc)})
                continue
            if revised in code_set:
                statuses.append({"attempt": attempt + 1, "status": "no_change"})
                continue
            self._write_log(
                workspace,
                f"RepairStatus{code_version + 1}",
                {"status": "changed", "attempt": attempt + 1, "attempts": statuses},
            )
            self._write_log(workspace, f"Code{code_version + 1}", revised)
            return revised

        # Preserve the latest valid code as a no-progress fallback. This keeps
        # the historical maximum-repair-loop behavior while avoiding an
        # exception caused only by duplicate/malformed repair responses.
        self._write_log(
            workspace,
            f"RepairStatus{code_version + 1}",
            {"status": "no_progress_fallback", "attempts": statuses},
        )
        self._write_log(workspace, f"Code{code_version + 1}", original_code)
        return original_code

    def _test_code(self, workspace, code_version):
        llm_api = UnifiedLLMAPI()

        # Read task_id from log.json
        log_file_path = os.path.join(workspace, "log.json")
        try:
            with open(log_file_path, "r") as f:
                log_data = json.load(f)
                task_id = log_data.get("task_id")
        except Exception as e:
            raise FileNotFoundError(f"Failed to read log.json in workspace: {e}")

        if task_id is None:
            raise ValueError("Task ID is missing in the log.json file.")

        # Log the task_id for debugging
        print(f"Running _test_code for Task ID: {task_id}, Code Version: {code_version}")

        test_script_path_parent = os.path.join(os.path.dirname(workspace))
        test_script_path = os.path.join(test_script_path_parent, "test_suites", f"test_suite_{task_id}.py")

        print(f"Test_script_path: {test_script_path}")

        # write test script according the raw example
        if not os.path.exists(test_script_path):
            raise Exception("Did not find the test script")

        # workspace paths
        current_dir = os.path.join(workspace, "../test_suites")


        # Convert paths to forward slashes for compatibility
        base_dir = os.path.join(workspace).replace("\\", "/")
        log_dir = os.path.join(workspace, "test_result", "log_files").replace("\\", "/")
        report_base_dir = os.path.join(workspace, "test_result", "inconsistency_files").replace("\\", "/")

        # Ensure log and report directories exist
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(report_base_dir, exist_ok=True)

        # Path to config file

        config_template_path = os.path.join(current_dir, "config_template.py")
        config_path = os.path.join(current_dir, "config.py")

        # Copy the config template to config.py
        shutil.copyfile(config_template_path, config_path)

        # Replace placeholders in config.py
        with open(config_path, "r") as f:
            config_content = f.read()
        config_content = config_content.replace("##PATH##TO##RESPONSE##", base_dir)
        config_content = config_content.replace("##PATH##TO##LOG##FILES##", log_dir)
        config_content = config_content.replace("##PATH##TO##INCONSISTENCY##FILES##", report_base_dir)
        with open(config_path, "w") as f:
            f.write(config_content)

        # DEBUG: Log the modified config file
        print("Config file after substitution:")
        with open(config_path, "r") as f:
            print(f.read())

        # get the code script
        # Run pytest
        try:
            pytest_result = subprocess.run(
                ["pytest", test_script_path, f"--code_version={code_version}"], check=True, capture_output=True, text=True
            )
            print("Pytest Output:\n", pytest_result.stdout)
            self._write_log(workspace, f"ScriptResult{code_version}", pytest_result.stdout)
        except subprocess.CalledProcessError as e:
            error_message = (
                f"Error during pytest execution.\n"
                f"Exit Code: {e.returncode}\n"
                f"STDOUT:\n{e.stdout or 'No stdout output'}\n"
                f"STDERR:\n{e.stderr or 'No stderr output'}"
            )
            print(error_message)
            self._write_log(workspace, f"ScriptError{code_version}", error_message)
            raise RuntimeError(
                f"Pytest failed for code_version={code_version}. See log for details."
            )
            # self._write_log(workspace, f"ScriptError{code_version}", e.stderr)
            # print("Error during pytest execution. Capturing details...")
            # print("Pytest stdout:\n", e.stdout)
            # print("Pytest stderr:\n", e.stderr)
            # raise RuntimeError(f"Pytest failed for code_version={code_version}. Details:\n{e.stderr}")

         # Parse bias summary from log files
        try:
            parse_script = os.path.join(current_dir, "..", "parse_bias_info.py")
            bias_info_dir = os.path.join(workspace, "test_result", "bias_info_files")
            sampling = int(code_version) + 1
            parse_command = ["python", parse_script, log_dir, bias_info_dir, f"{sampling}"]  # Sampling is set to 1
            parse_result = subprocess.run(parse_command, check=True, capture_output=True, text=True)
            print("Bias Info Parsing Output:", parse_result.stdout)
        except subprocess.CalledProcessError as e:
            print("Error during bias info parsing:", e.stderr)
            raise

        # Check if the expected JSON file exists
        task_id = self._get_information_from_log(workspace, "task_id")
        bias_info_file = os.path.join(bias_info_dir, f"bias_info{task_id}.jsonl")
        if not os.path.exists(bias_info_file):
            print("Bias info JSON file not found. Returning error status.")
            return "CodeFailExecute"

        # generate test report
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_test_code.json")
        bias_info = get_bias_info_from_jsonl(os.path.join(bias_info_dir, f"bias_info{task_id}.jsonl"), code_version)
        if bias_info != "none":
            prompt["Context"] = f"The code shows the bias in " + str(bias_info) + ". Please remove the bias."
            result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
            self._write_log(workspace, f"TestReport{code_version}", result)
        return bias_info

    def unify_bugfix_test_iteration(self, workspace, **kwargs):
        final_code = self._get_information_from_log(workspace, "Code0")
        i = 0
        while True:
            response = self._test_code(workspace, i)
            response = response.lower()
            print("response", response)
            # response = response[:response.find("\n")]
            if response == "none":
                self._write_log(workspace, f"FinalCode", final_code)
                break
            if response == "CodeFailExecute":
                self._write_log(workspace, f"FinalCode", final_code)
                self._write_log(workspace, f"ExecuteInfo", "code can not execute")
                break
            if len(set(response)) == 1 and response[0] == ".":
                break
            if i == 1:
                break
            final_code = self._repair_code(workspace, i)
            i += 1
        self._write_log(workspace, f"FinalCode", final_code)
        return final_code

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
