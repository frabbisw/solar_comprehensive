#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util
"""
import os
import json
from utils.keys.unified_llm_api import UnifiedLLMAPI
from utils.keys.base_key import BaseKey


class TestCasesDesign(BaseKey):
    version_map = {
        "0.0.1": "waterfall",
        "0.0.3": "tdd_write_test_cases_with_meetings",
    }

    def get_waterfall_prompt(self, workspace, openai_api):
        prompt = openai_api.generate_prompt_from_unify_prompt("unify_write_test_cases.json")
        prd = self._get_information_from_log(workspace, "Final PRD")
        design = self._get_information_from_log(workspace, "Final Design")
        prompt["Context"] = f"# ProductRequirementDocument:\n{prd}\n# Design:\n{design}"
        prompt["Question"] = self._get_raw_question(workspace)
        return json.dumps(prompt)

    def tdd_write_test_cases_with_meetings(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()

        # draft
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_write_test_cases.json")
        analyze = self._get_information_from_log(workspace, "Analyze")
        prompt["Context"] = f"# Requirement Analysis:\n{analyze}"
        prompt["Question"] = self._get_raw_question(workspace)
        draft = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, "Test Cases Draft", draft, prompt=json.dumps(prompt))

        # meetings
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_test_cases_meetings.json")
        prompt["Context"] = self._get_information_from_log(workspace, "Test Cases Draft")
        review = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'Test Cases Meetings', review, prompt=json.dumps(prompt))

        # revise version
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_revise_test_cases.json")
        prompt["Context"] = f"# Suggestions:\n{review}\n # Draft Test cases:\n{draft}"
        prompt["Question"] += self._get_raw_question(workspace)
        result = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'Test Cases', result, prompt=json.dumps(prompt))
        return result

    def waterfall(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()
        prompt = self.get_waterfall_prompt(workspace, llm_api)
        result = llm_api.execute("default_json_prompt", prompt=prompt)["content"]
        self._write_log(workspace, "Test Cases", result, prompt=prompt)
        return result

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
