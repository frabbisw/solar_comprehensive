#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" base keys class
"""
import datetime
import os
import subprocess
import json
from abc import ABC, abstractmethod
from utils.workflow import return_root_absolute_path


class BaseKey(ABC):
    templates_path = os.path.join(return_root_absolute_path(), "Templates")
    format_prompt_templates = os.path.join(templates_path, "prompt_templates", "version1.1")
    unify_prompt_templates = os.path.join(templates_path, "prompt_templates", "version1.2")

    def extract_definition_from_question(self, question):
        result = list()
        data = question.split("\n")
        while len(data) > 0:
            each_line = data.pop(0)
            result.append(each_line)
            if each_line.startswith("def"):
                break
        return "\n".join(result)

    def extract_comment_from_question(self, question):
        result = list()
        flag = False
        data = question.split("\n")
        while len(data) > 0:
            each_line = data.pop(0)
            if each_line.startswith("def"):
                flag = True
                continue
            if flag:
                result.append(each_line)
        return "\n".join(result)

    def _get_information_from_log(self, workspace, key):
        with open(os.path.join(workspace, "log.json"), "r") as f:
            log = json.load(f)
            return log[key]

    def _get_raw_question(self, workspace):
        return self._get_information_from_log(workspace, 'task')

    def _run_command(self, command):
        try:
            out_bytes = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, timeout=480)
        except subprocess.CalledProcessError as e:
            out_bytes = e.output  # Output generated before error
            code = e.returncode  # Return code
        return out_bytes.decode("utf8")

    def _write_log(self, workspace, key, value, **kwargs):
        print(F"Write Log: {key}")
        with open(os.path.join(workspace, "log.json"), "r") as f:
            log = json.load(f)
            log[key] = value
            log["datetime"] = log.get("datetime", dict())
            log["datetime"][key] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "prompt" in kwargs:
                log[f"{key}_prompt"] = kwargs["prompt"]
        with open(os.path.join(workspace, "log.json"), "w") as f:
            json.dump(log, f, indent=4)

    @property
    @abstractmethod
    def version_map(self):
        pass

    @abstractmethod
    def execute(self, version, **kwargs):
        pass


if __name__ == "__main__":
    pass
