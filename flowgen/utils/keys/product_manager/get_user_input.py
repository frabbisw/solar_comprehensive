#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util: get user input, like get the project task from user
"""
import json
import os.path
from utils.keys.base_key import BaseKey


class GetUserInput(BaseKey):
    version_map = {
        "0.0.2": "get_input_from_dataset",
    }

    def get_input_from_dataset(self, workspace, **kwargs):
        task = kwargs["task"]
        task_id = kwargs.get("task_id", "unknown")
        workflow = kwargs["workflow"]
        entry_point = kwargs.get("entry_point", "unknown")
        self._write_log(workspace, 'task', task)
        self._write_log(workspace, 'task-id', task_id)
        self._write_log(workspace, 'workflow', workflow)
        self._write_log(workspace, 'entry_point', entry_point)
        return task

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
