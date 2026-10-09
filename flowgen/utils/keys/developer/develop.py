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


class Develop(BaseKey):
    version_map = {
        "0.0.2": "waterfall",
        "0.0.4": "tdd_write_code_with_meetings",
    }

    def get_waterfall_prompt(self, workspace, openai_api):
        prompt = openai_api.generate_prompt_from_unify_prompt("unify_write_code.json")
        prompt["Question"] += self._get_raw_question(workspace)

        # Normal Waterfall uses Final Design.  For the manuscript's role
        # ablations, removed upstream roles cannot leave dangling dependencies:
        #   - No Architect + Tester: Developer consumes Final PRD directly.
        #   - Developer Only: Developer consumes the raw task directly.
        # This preserves the same Developer prompt/agent while removing only
        # the named roles.
        try:
            design = self._get_information_from_log(workspace, "Final Design")
        except KeyError:
            design = ""
        try:
            prd = self._get_information_from_log(workspace, "Final PRD")
        except KeyError:
            prd = ""
        if not prd:
            try:
                prd = self._get_information_from_log(workspace, "Original PRD")
            except KeyError:
                prd = ""

        if design:
            prompt["Context"] = f"# Design:\n{design}"
        elif prd:
            prompt["Context"] = f"# Product Requirement Document:\n{prd}"
        else:
            prompt["Context"] = "# No upstream PRD or design is available in this ablation."
        return json.dumps(prompt)

    def waterfall(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()
        prompt = self.get_waterfall_prompt(workspace, llm_api)
        result = llm_api.execute("default", prompt=prompt)["content"]
        if "```python" in result:
            result = re.findall(r"```python\n([\s\S]+)```", result)[0]
        self._write_log(workspace, "Code0Draft", result, prompt=prompt)
        return result

    def tdd_write_code_with_meetings(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()

        # draft
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_write_code.json")
        test_cases = self._get_information_from_log(workspace, "Test Cases")
        design = self._get_information_from_log(workspace, "Design")
        prompt["Context"] = f"# Test Cases:\n{test_cases}\n# Design:\n{design}"
        prompt["Question"] += self._get_raw_question(workspace)
        draft = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        if "```python" in draft:
            draft = re.findall(r"```python\n([\s\S]+)```", draft)[0]
        self._write_log(workspace, "Code0draft", draft, prompt=json.dumps(prompt))

        # meetings
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_code_review_meetings.json")
        prompt["Context"] = self._get_information_from_log(workspace, "Code0draft")
        review = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'Code Review Meetings', review)

        # revise version
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_revise_code.json")
        prompt["Context"] = f"# Suggestions:\n{review}\n# Original code:\n{draft}"
        prompt["Question"] += self._get_raw_question(workspace)
        result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'Code0', result, prompt=json.dumps(prompt))
        return result

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
