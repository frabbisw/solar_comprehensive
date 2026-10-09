#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util
"""
import os
import json
from utils.keys.unified_llm_api import UnifiedLLMAPI
from utils.keys.base_key import BaseKey


class ReviseDesign(BaseKey):
    version_map = {
        "0.0.1": "unify"
    }

    def unify(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_revise_design.json")
        design = self._get_information_from_log(workspace, "Original_architect_design")
        advices = self._get_information_from_log(workspace, "Design Review")
        prompt["Context"] = f"# Suggestions:\n{advices}"
        prompt["Question"] += design
        result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, f"Final Design", result, prompt=json.dumps(prompt))
        return result

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
