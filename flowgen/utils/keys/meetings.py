#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util
"""
import copy
import os
import json
from abc import ABC, abstractmethod
from utils.keys.unified_llm_api import UnifiedLLMAPI
from utils.keys.base_key import BaseKey


class Meetings(BaseKey):
    def default(self, workspace, **kwargs):
        llm_api = UnifiedLLMAPI()
        meeting_result = dict()
        meet_members = kwargs.get("meet_members", None)
        review_key = kwargs.get("review_key", None)
        review_template = kwargs.get("review_template", None)
        extra_content = kwargs.get("extra_content", None)
        review_content = self._get_information_from_log(workspace, review_key)

        for each_member in meet_members:
            prompt = llm_api.generate_prompt_from_format_prompt(review_template)
            prompt["Role"] = f"You are a professional {each_member} in the software development team"
            if extra_content:
                prompt["Context"] = extra_content
            prompt["Context"] += review_content
            prompt = json.dumps(prompt)
            result = llm_api.execute("default", prompt=prompt)
            meeting_result[each_member] = result["content"]
        return meeting_result

    @abstractmethod
    def version_map(self):
        pass

    @abstractmethod
    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)
