#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" utils for workflow
"""
import datetime
import json
import os.path


def return_root_absolute_path():
    return os.path.dirname(os.path.join(os.path.dirname(__file__)))


class Workflow:
    def _import(self, role_module, key_name):
        if "module" in role_module:
            module = __import__(f"utils.keys.{role_module['module']}.{key_name}", fromlist=[role_module[key_name]])
        else:
            module = __import__(f"utils.keys.{key_name}", fromlist=[role_module[key_name]])
        return module

    def _check_steps(self, steps_list):
        with open(os.path.join(os.path.dirname(__file__), "keys", "keys.json")) as f:
            class_names = json.load(f)
            for each_step in steps_list:
                key_name = each_step["key"]
                role = each_step["leader"]
                role_module = class_names[role] if role in class_names else class_names
                assert key_name in role_module, f"Key:{role_module}.{key_name} not in keys.json"
                self._import(role_module, key_name)

    def loads_workflow(self, file_path):
        with open(file_path) as f:
            workflow = json.load(f)
            for each_stage in workflow:
                self._check_steps(each_stage["steps"])
        return workflow

    def do_step(self, step_dict, executor, **kwargs):
        with open(os.path.join(os.path.dirname(__file__), "keys", "keys.json")) as f:
            class_names = json.load(f)
            role_ability = class_names[executor] if executor in class_names else class_names
            key_name = step_dict["key"]
            module = self._import(role_ability, key_name)
        klass = getattr(module, role_ability[key_name])
        print(klass().execute(step_dict["key version"], **kwargs))

    def create_workspace(self, task_id=None):
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        workspace_root = os.getenv(
            "FLOWGEN_WORKSPACE_ROOT",
            os.path.join(return_root_absolute_path(), "workspace"),
        )
        run_id = os.getenv("FLOWGEN_RUN_ID", "").strip()
        if run_id:
            workspace_root = os.path.join(workspace_root, run_id)
        if task_id is not None and run_id:
            workspace = os.path.join(workspace_root, f"task_{task_id}")
        else:
            workspace = os.path.join(workspace_root, now)
        os.makedirs(workspace, exist_ok=True)
        json_log = {"start_time": now}
        if task_id is not None:
            json_log["task_id"] = task_id
        with open(os.path.join(workspace, "log.json"), "w") as f:
            json.dump(json_log, f, indent=4)
        return workspace


if __name__ == "__main__":
    pass
