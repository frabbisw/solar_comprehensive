#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util
"""
import os
import json
from utils.keys.unified_llm_api import UnifiedLLMAPI
from utils.keys.base_key import BaseKey


class ReviseCode(BaseKey):
    version_map = {
        "0.0.4": "unify",
    }

    def unify(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_revise_code.json")
        code = self._get_information_from_log(workspace, "Code0Draft")
        advices = self._get_information_from_log(workspace, "Code Review")
        prompt["Context"] = f"# Original Code:\n{code}\n# Advices:\n{json.dumps(advices)}"
        result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, f"Code0Revise", result, prompt=json.dumps(prompt))
        return result


    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
