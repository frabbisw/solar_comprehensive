#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util
"""
import os
import json
import re

from utils.keys.unified_llm_api import UnifiedLLMAPI
from utils.keys.base_key import BaseKey
from utils.json_utils import parse_first_json_object, get_required_string


class BUGFIX_TEST_Iteration(BaseKey):
    version_map = {
        "0.0.1": "unify_bugfix_test_iteration",
    }

    def _repair_code(self, workspace, code_version):
        openai_api = UnifiedLLMAPI()
        prompt = openai_api.generate_prompt_from_unify_prompt("unify_repair_code.json")
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
            raw = openai_api.execute("default_json_prompt", prompt=prompt)["content"]
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
        openai_api = UnifiedLLMAPI()
        test_script_path = os.path.join(workspace, "test_script.py")
        # write test script according the raw example
        if not os.path.exists(test_script_path):
            prompt = openai_api.generate_prompt_from_unify_prompt("unify_write_test_script.json")
            prompt["Question"] = self._get_raw_question(workspace)
            prompt = json.dumps(prompt)
            result = openai_api.execute("default", prompt=prompt)["content"]
            self._write_log(workspace, f"TestScriptOriginal", result, prompt=prompt)
            result = re.sub(r"(def[\s\S]+)class Test", "class Test", result)
            self._write_log(workspace, f"TestScript", result, prompt=prompt)

        # run test script
        with open(test_script_path, "w", encoding="utf8") as f:
            f.write(self._get_information_from_log(workspace, f"Code{code_version}"))
            f.write(f"\n{self._get_information_from_log(workspace, 'TestScript')}")
        script_result = self._run_command(f"python {test_script_path}")
        self._write_log(workspace, f"ScriptResult{code_version}", script_result)

        # generate test report
        prompt = openai_api.generate_prompt_from_unify_prompt("unify_test_code.json")
        prompt["Context"] = script_result
        result = openai_api.execute("default", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, f"TestReport{code_version}", result)
        return script_result

    def unify_bugfix_test_iteration(self, workspace, **kwargs):
        final_code = self._get_information_from_log(workspace, "Code0")
        i = 0
        while True:
            response = self._test_code(workspace, i)
            response = response.lower()
            response = response.splitlines()[0] if response.splitlines() else response
            if response and len(set(response)) == 1 and response[0] == ".":
                break
            if i == 2:
                break
            final_code = self._repair_code(workspace, i)
            i += 1
        self._write_log(workspace, f"FinalCode", final_code)
        return final_code

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
