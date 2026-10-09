#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util
"""
import json
import os
from utils.keys.base_key import BaseKey
from utils.keys.unified_llm_api import UnifiedLLMAPI


class AnalyzeUserInput(BaseKey):
    version_map = {
        "0.0.2": "waterfall",
        "0.0.4": "tdd_analyze_with_meetings"
    }

    def _prompt_for_waterfall(self, workspace, openai_api):
        prompt = openai_api.generate_prompt_from_unify_prompt("unify_write_analyze.json")
        prompt["Role"] += "Product Requirement Document"
        prompt["Question"] += self._get_raw_question(workspace)
        return json.dumps(prompt)

    def waterfall(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()
        prompt = self._prompt_for_waterfall(workspace, llm_api)
        result = llm_api.execute("default_json_prompt", prompt=prompt)["content"]
        self._write_log(workspace, 'Original PRD', result, prompt=prompt)
        return result

    def tdd_analyze_with_meetings(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()

        # Draft version
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_write_analyze.json")
        prompt["Role"] += "requirement analyst"
        prompt["Question"] += self._get_raw_question(workspace)
        draft = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'AnalyzeDraft', draft)

        # meetings
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_analyze_meetings.json")
        prompt["Context"] = draft
        review = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'AnalyzeMeetings', review)

        # revise version
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_revise_analyze.json")
        prompt["Context"] = f"# Suggestion:\n{review}"
        prompt["Question"] += draft
        result = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'Analyze', result)

        return result

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
