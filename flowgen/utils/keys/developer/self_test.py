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


class SelfTest(BaseKey):
    version_map = {
        "0.0.1": "unify"
    }

    def unify(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_self_test.json")
        original_code = self._get_information_from_log(workspace, "Code0Revise")
        testcases = self._get_information_from_log(workspace, "Final Test Cases")
        prompt["Context"] = f"# Original Code:\n{original_code}\n# Test Cases:\n{testcases}"
        prompt["Question"] = self._get_raw_question(workspace)
        result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        if "```python" in result:
            result = re.findall(r"```python\n([\s\S]+)```", result)[0]
        self._write_log(workspace, 'Code0', result, prompt=json.dumps(prompt))
        return result

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
