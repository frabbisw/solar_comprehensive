#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util
"""
import os
import json
from utils.keys.unified_llm_api import UnifiedLLMAPI
from utils.keys.meetings import Meetings


class CodeReviewMeeting(Meetings):
    version_map = {
        "0.0.4": "unify",
    }

    def unify(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_code_review_meetings.json")
        draft = self._get_information_from_log(workspace, 'Code0Draft')
        prompt["Context"] = draft
        review = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'Code Review', review, prompt=json.dumps(prompt))
        return review

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
