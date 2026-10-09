#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util
"""
import os
import json
from utils.keys.unified_llm_api import UnifiedLLMAPI
from utils.keys.base_key import BaseKey


class ArchitectDesign(BaseKey):
    version_map = {
        "0.0.2": "waterfall",
        "0.0.4": "tdd_design_with_meetings",
    }

    def format_for_waterfall(self, workspace, openai_api):
        prompt = openai_api.generate_prompt_from_unify_prompt("unify_write_design.json")

        # Normal Waterfall consumes the Product Manager's Final PRD.  The
        # RQ3 role-ablation "No Requirement Engineer + Tester" removes that
        # upstream role.  In that configuration the Architect receives the
        # original task directly, which is the minimal faithful handoff when
        # the requirement role is absent.
        try:
            final_prd = self._get_information_from_log(workspace, "Final PRD")
        except KeyError:
            final_prd = ""

        if final_prd:
            prompt["Context"] = f"# Product Requirement Document:\n{final_prd}"
        else:
            prompt["Context"] = "# No separate requirement document is available in this ablation."
        prompt["Question"] += self._get_raw_question(workspace)
        return json.dumps(prompt)

    def tdd_design_with_meetings(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()

        # draft
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_write_design.json")
        analyze = self._get_information_from_log(workspace, "Analyze")
        prompt["Context"] = f"# Requirement Analysis:\n{analyze}"
        prompt["Question"] += self._get_raw_question(workspace)
        draft = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, "DesignDraft", draft)

        # meetings
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_design_meetings.json")
        prompt["Context"] = self._get_information_from_log(workspace, "DesignDraft")
        review = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'DesignMeetings', review)

        # revise version
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_revise_design.json")
        prompt["Context"] = f"#Suggestions:\n{review}\n"
        prompt["Question"] += self._get_information_from_log(workspace, "DesignDraft")
        result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'Design', result)

        return result

    def waterfall(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()
        prompt = self.format_for_waterfall(workspace, llm_api)
        result = llm_api.execute("default", prompt=prompt)["content"]
        self._write_log(workspace, "Original_architect_design", result, prompt=prompt)
        return result

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
