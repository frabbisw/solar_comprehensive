#!/bin/env python3
# -*- coding: utf-8 -*-
# version: Python3.X
""" util
"""
import os
import json
import re
import threading
from queue import Queue
from utils.keys.unified_llm_api import UnifiedLLMAPI
from utils.keys.base_key import BaseKey
from utils.json_utils import parse_first_json_object, get_required_string


class Sprint(BaseKey):
    def __init__(self):
        super().__init__()
        self.multiple_times = 20

    version_map = {
        "0.0.3": "disordered",
        "0.0.5": "codet_like",
    }

    def _agile_architect(self, workspace, tasks_list, sprint_times):
        llm_api = UnifiedLLMAPI()
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_write_design.json")
        user_stories = self._get_information_from_log(workspace, f"UserStory{sprint_times}")
        prompt["Context"] = f"# Tasks:\n{tasks_list}\n# UserStory:\n{user_stories}"
        prompt["Question"] += self._get_raw_question(workspace)
        result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, f"DesignDraft{sprint_times}", result)
        return result

    def _agile_architect_with_meetings(self, workspace, tasks_list, sprint_times):
        draft = self._agile_architect(workspace, tasks_list, sprint_times)
        llm_api = UnifiedLLMAPI()

        # meetings
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_design_meetings.json")
        prompt["Context"] = draft
        review = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, f"DesignMeetings{sprint_times}", review)

        # revise
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_revise_design.json")
        prompt["Context"] = f"# Suggestions:\n{review}"
        prompt["Question"] += draft
        result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, f"Design{sprint_times}", result)

        return result

    def _agile_developer(self, workspace, tasks_list, sprint_times):
        llm_api = UnifiedLLMAPI()
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_write_code.json")
        design = self._get_information_from_log(workspace, f"Design{sprint_times}")
        prompt["Context"] = f"# Tasks:\n{tasks_list}\n# Design:\n{design}"
        prompt["Question"] += self._get_raw_question(workspace)
        result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        if "```python" in result:
            result = re.findall(r"```python\n([\s\S]+)```", result)[0]
        self._write_log(workspace, f"CodeDraft{sprint_times}", result, prompt=prompt)
        return result

    def _agile_developer_repair(self, workspace, suggestions, sprint_times):
        llm_api = UnifiedLLMAPI()
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_repair_code.json")
        original_code = self._get_information_from_log(workspace, f"Code{sprint_times}")
        test_report = self._get_information_from_log(workspace, f"TestReport{sprint_times}")
        suggestions = json.dumps(suggestions)
        prompt["Context"] = f"# Test Report:\n{test_report}# suggestions:\n{suggestions}"
        prompt["Question"] += self._get_raw_question(workspace)

        code_set = set()
        for j in range(sprint_times + 1):
            code_set.add(self._get_information_from_log(workspace, f"Code{j}"))

        # Modern models sometimes wrap otherwise-valid JSON or decide the
        # current code already needs no change. Retry those cases and preserve
        # the latest valid code if all repair attempts make no progress.
        statuses = []
        for attempt in range(3):
            raw = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
            self._write_log(workspace, f"RepairResponse{sprint_times}", raw, prompt=prompt)
            try:
                obj = parse_first_json_object(raw)
                revised = get_required_string(obj, "revised_code")
            except ValueError as exc:
                statuses.append({"attempt": attempt + 1, "status": "parse_error", "detail": str(exc)})
                continue
            if revised in code_set:
                statuses.append({"attempt": attempt + 1, "status": "no_change"})
                continue
            self._write_log(
                workspace,
                f"RepairStatus{sprint_times + 1}",
                {"status": "changed", "attempt": attempt + 1, "attempts": statuses},
            )
            self._write_log(workspace, f"Code{sprint_times + 1}", revised)
            return revised

        original_code = self._get_information_from_log(workspace, f"Code{sprint_times}")
        self._write_log(
            workspace,
            f"RepairStatus{sprint_times + 1}",
            {"status": "no_progress_fallback", "attempts": statuses},
        )
        self._write_log(workspace, f"Code{sprint_times + 1}", original_code)
        return original_code

    def _agile_developer_with_meetings(self, workspace, tasks_list, sprint_times):
        draft = self._agile_developer(workspace, tasks_list, sprint_times)
        llm_api = UnifiedLLMAPI()
        # meetings
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_code_review_meetings.json")
        prompt["Context"] = draft
        review = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, f"CodeReviewMeetings{sprint_times}", review)

        # revise
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_revise_code.json")
        design = self._get_information_from_log(workspace, f"Design{sprint_times}")
        prompt["Context"] = f"# Tasks:\n{tasks_list}\n# Design:\n{design}# Suggestions:\n{review}"
        prompt["Question"] += self._get_raw_question(workspace)
        result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, f"Code{sprint_times}CR", result, prompt=json.dumps(prompt))

        return result

    def _agile_developer_self_test(self, workspace, sprint_times):
        llm_api = UnifiedLLMAPI()
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_self_test.json")
        original_code = self._get_information_from_log(workspace, f"Code{sprint_times}CR")
        testcases = self._get_information_from_log(workspace, "Test Cases")
        prompt["Context"] = f"# Original Code:\n{original_code}\n# Test Cases:\n{testcases}"
        prompt["Question"] = self._get_raw_question(workspace)
        result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        if "```python" in result:
            result = re.findall(r"```python\n([\s\S]+)```", result)[0]
        self._write_log(workspace, f'Code{sprint_times}', result, prompt=prompt)
        return result

    def _agile_scrum_master(self, workspace, sprint_times):
        llm_api = UnifiedLLMAPI()
        with open(os.path.join(workspace, "log.json"), "r", encoding="utf8") as f:
            log = json.load(f)
            prompt = llm_api.generate_prompt_from_format_prompt("agile_sprint_scrum_master.json")
            prompt["Context"] = log[f"TestReport{sprint_times}"]
            result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
            self._write_log(workspace, f"ScrumCheck{sprint_times}", result)
        return result

    def _disordered_meeting(self, workspace, history, role):
        llm_api = UnifiedLLMAPI()
        for i in range(2):
            prompt = llm_api.generate_prompt_from_format_prompt("agile_disordered_meeting_discuss.json")

            prompt["Role"] += role
            prompt["Context"] = "\n".join(history.queue)

            prompt = json.dumps(prompt)
            result = llm_api.execute("default", prompt=prompt)["content"]
            history.put(f"[{role}]says: {result}\n-----\n")

    def _disordered_sprint_review(self, workspace, sprint_times):
        llm_api = UnifiedLLMAPI()
        q = Queue()
        test_report = self._get_information_from_log(workspace, f"TestReport{sprint_times}")
        q.put(f"[ScrumMaster]says: Here is our test Report: {test_report}, do you have any ideas?\n-----\n")
        thread_list = list()
        roles = ["ProductOwner", "Architect", "Developer", "Tester"]

        for role in roles:
            thread_list.append(threading.Thread(target=self._disordered_meeting, args=(workspace, q, role)))
        for each_thread in thread_list:
            each_thread.start()
        for each_thread in thread_list:
            each_thread.join()

        self._write_log(workspace, f"SprintReview{sprint_times}", "\n".join(q.queue))
        prompt = llm_api.generate_prompt_from_format_prompt("agile_disordered_meeting_suggestions.json")
        prompt["Context"] = "\n".join(q.queue)
        prompt = json.dumps(prompt)
        result = llm_api.execute("default_json_prompt", prompt=prompt)["content"]
        self._write_log(workspace, f"SprintReviewMeetings{sprint_times}", result, prompt=prompt)

        return result

    def _agile_product_owner(self, workspace, tasks_list, sprint_times):
        llm_api = UnifiedLLMAPI()
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_write_analyze.json")
        prompt["Role"] += "UserStory"
        prompt["Context"] = tasks_list
        prompt["Question"] += self._get_raw_question(workspace)
        result = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, f"UserStoryDraft{sprint_times}", result, prompt=json.dumps(prompt))

        # meetings
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_analyze_meetings.json")
        prompt["Context"] = result
        review = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'AnalyzeMeetings', review)

        # revise
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_revise_analyze.json")
        prompt["Context"] = f"# Suggestion:\n{review}"
        prompt["Question"] += result
        result = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, f'UserStory{sprint_times}', result, prompt=prompt)
        return result

    def _agile_tester(self, workspace, tasks_list, sprint_times):
        llm_api = UnifiedLLMAPI()

        # draft
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_write_test_cases.json")
        user_story = self._get_information_from_log(workspace, f"UserStory{sprint_times}")
        design = self._get_information_from_log(workspace, f"Design{sprint_times}")
        prompt["Context"] = f"# UsrtStory:\n{user_story}\n# Tasks:\n{tasks_list}\n# Design:\n{design}"
        prompt["Question"] = self._get_raw_question(workspace)
        draft = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, "Test Cases Draft", draft, prompt=json.dumps(prompt))

        # meetings
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_test_cases_meetings.json")
        prompt["Context"] = self._get_information_from_log(workspace, "Test Cases Draft")
        review = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'Test Cases Meetings', review)

        # revise version
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_revise_test_cases.json")
        prompt["Context"] = f"# Suggestions:\n{review}\n # Draft Test cases:\n{draft}"
        prompt["Question"] += self._get_raw_question(workspace)
        result = llm_api.execute("default_json_prompt", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, 'Test Cases', result, prompt=json.dumps(prompt))
        return result

    def _remove_sparse_code(self, workspace, code):
        code = re.sub(r"(def[\s\S]+)class Test", "class Test", code)
        if "```python" in code:
            code = re.findall(r"```python\n([\s\S]+)```", code)[0]
        return code

    def _agile_tester_interpreter(self, workspace, sprint_times):
        llm_api = UnifiedLLMAPI()
        test_script_path = os.path.join(workspace, "test_script.py")
        # write test script according the raw example
        if not os.path.exists(test_script_path):
            prompt = llm_api.generate_prompt_from_unify_prompt("unify_write_test_script.json")
            prompt["Question"] = self._get_raw_question(workspace)
            prompt = json.dumps(prompt)
            result = llm_api.execute("default", prompt=prompt)["content"]
            self._write_log(workspace, f"TestScriptOriginal", result, prompt=prompt)
            result = self._remove_sparse_code(workspace, result)
            self._write_log(workspace, f"TestScript", result)

        # run test script
        with open(test_script_path, "w", encoding="utf8") as f:
            f.write(self._get_information_from_log(workspace, f"Code{sprint_times}"))
            f.write(f"\n{self._get_information_from_log(workspace, 'TestScript')}")
        test_result = self._run_command(f"python {test_script_path}")
        self._write_log(workspace, f"ScriptResult{sprint_times}", test_result)

        # generate test report
        prompt = llm_api.generate_prompt_from_unify_prompt("unify_test_code.json")
        script_result = self._get_information_from_log(workspace, f'ScriptResult{sprint_times}')
        prompt["Context"] = f"# test script's output:\n{script_result}"
        prompt["Question"] += self._get_information_from_log(workspace, f"Code{sprint_times}")
        result = llm_api.execute("default", prompt=json.dumps(prompt))["content"]
        self._write_log(workspace, f"TestReport{sprint_times}", result)
        return test_result

    def _get_task_lists(self, workspace):
        with open(os.path.join(workspace, "log.json"), "r", encoding="utf8") as f:
            log = json.load(f)
            return parse_first_json_object(log["TasksList"])

    def _get_disordered_task_lists(self, workspace):
        with open(os.path.join(workspace, "log.json"), "r", encoding="utf8") as f:
            log = json.load(f)
            return parse_first_json_object(log["DisorderedSprintMeetings"])

    def disordered(self, workspace, **kwargs):
        sprint_times, code = 0, "Unknown"
        tasks_list = self._get_disordered_task_lists(workspace)
        self._agile_product_owner(workspace, tasks_list['product-owner'], sprint_times)
        self._agile_architect_with_meetings(workspace, tasks_list['architect'], sprint_times)
        code = self._agile_developer_with_meetings(workspace, tasks_list['developer'], sprint_times)
        self._write_log(workspace, f"FinalCode", code)
        self._agile_tester(workspace, tasks_list['tester'], sprint_times)
        code = self._agile_developer_self_test(workspace, sprint_times)
        self._write_log(workspace, f"FinalCode", code)

        while True:
            test_result = self._agile_tester_interpreter(workspace, sprint_times)
            first_line = test_result.splitlines()[0] if test_result.splitlines() else test_result
            test_result = first_line
            if len(set(test_result)) == 1 and test_result[0] == ".":
                break
            if sprint_times >= 1:
                break
            suggestions_list = parse_first_json_object(
                self._disordered_sprint_review(workspace, sprint_times)
            )
            code = self._agile_developer_repair(workspace, suggestions_list, sprint_times)
            self._write_log(workspace, f"FinalCode", code)
            sprint_times += 1
        return code

    def execute(self, version, **kwargs):
        return getattr(self, self.version_map[version])(**kwargs)


if __name__ == "__main__":
    pass
