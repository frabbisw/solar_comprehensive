#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util
"""
import os
import json
from utils.keys.unified_llm_api import UnifiedLLMAPI

from utils.keys.base_key import BaseKey


class ReviseTestCases(BaseKey):
    version_map = {
        "0.0.1": "unify"
    }

    def unify(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()

        prompt = llm_api.generate_prompt_from_unify_prompt("unify_revise_test_cases.json")
        testcases = self._get_information_from_log(workspace, "Test Cases")
        advices = self._get_information_from_log(workspace, "Test Cases Review")
        prompt["Context"] = f"# Suggestions:\n{advices}\n # Draft Test cases:\n{testcases}"
        prompt["Question"] += self._get_raw_question(workspace)
        result = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'Final Test Cases', result, prompt=json.dumps(prompt))
        return result

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
