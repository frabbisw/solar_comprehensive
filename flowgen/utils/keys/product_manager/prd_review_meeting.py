#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
"""
"""
import json
import os
from utils.keys.unified_llm_api import UnifiedLLMAPI
from utils.keys.meetings import Meetings


class PRDReviewMeeting(Meetings):
    version_map = {
        "0.0.1": "unify",
    }

    def unify(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_analyze_meetings.json")
        prompt["Context"] = self._get_information_from_log(workspace, "Original PRD")
        review = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'PRD Review', review)
        return review

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
