#!/usr/bin/env python3
"""Run one SocialBias-Bench configuration through the handed-over FlowGen code.

The revision exposes the 12 unique RQ3 configurations reported/described in
our manuscript:

  Workflow structure:
    raw, waterfall, scrum

  Fairness-aware role prompting (Waterfall):
    waterfall_pm_fair, waterfall_architect_fair,
    waterfall_developer_fair, waterfall_qa_fair, waterfall_all_fair

  Role ablation (Waterfall):
    no_tester, no_architect_tester, no_requirement_tester, developer_only

The original hand-off did not contain source files for the four role-ablation
variants.  They are reconstructed here from the manuscript definition by
removing the named role stages from the Waterfall process.  When an upstream
role is removed, the remaining downstream role consumes the closest available
artifact (PRD, design, or raw task); see docs/RQ3_ABLATION_IMPLEMENTATION.md.

Model, reasoning effort, and service configuration are read from the root .env.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from itertools import islice
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from utils.workflow import Workflow  # noqa: E402
from code_utils import normalize_generated_code  # noqa: E402


CONFIGS = {
    # Workflow-structure experiment
    "raw": {
        "workflow": "rawGPT/rawGPT.json",
        "fairness_role": "none",
        "group": "workflow_structure",
    },
    "waterfall": {
        "workflow": "waterfall/waterfall.json",
        "fairness_role": "none",
        "group": "workflow_structure",
    },
    "scrum": {
        "workflow": "scrum/scrum.json",
        "fairness_role": "none",
        "group": "workflow_structure",
    },
    # Fairness-aware role prompting
    "waterfall_pm_fair": {
        "workflow": "waterfall/waterfall.json",
        "fairness_role": "product_manager",
        "group": "fairness_role_prompting",
    },
    "waterfall_architect_fair": {
        "workflow": "waterfall/waterfall.json",
        "fairness_role": "architect",
        "group": "fairness_role_prompting",
    },
    "waterfall_developer_fair": {
        "workflow": "waterfall/waterfall.json",
        "fairness_role": "developer",
        "group": "fairness_role_prompting",
    },
    "waterfall_qa_fair": {
        "workflow": "waterfall/waterfall.json",
        "fairness_role": "qa",
        "group": "fairness_role_prompting",
    },
    "waterfall_all_fair": {
        "workflow": "waterfall/waterfall.json",
        "fairness_role": "all",
        "group": "fairness_role_prompting",
    },
    # Role ablation. Baseline is the same clean `waterfall` configuration.
    "no_tester": {
        "workflow": "ablations/no_tester.json",
        "fairness_role": "none",
        "group": "role_ablation",
    },
    "no_architect_tester": {
        "workflow": "ablations/no_architect_tester.json",
        "fairness_role": "none",
        "group": "role_ablation",
    },
    "no_requirement_tester": {
        "workflow": "ablations/no_requirement_tester.json",
        "fairness_role": "none",
        "group": "role_ablation",
    },
    "developer_only": {
        "workflow": "ablations/developer_only.json",
        "fairness_role": "none",
        "group": "role_ablation",
    },
}

# Backward-compatible direct workflow names for ad-hoc debugging.
WORKFLOWS = {
    "raw": "rawGPT/rawGPT.json",
    "waterfall": "waterfall/waterfall.json",
    "scrum": "scrum/scrum.json",
}


def read_prompts(path: Path, start: int, end: int):
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(islice(f, start, end), start=start):
            if not line.strip():
                continue
            obj = json.loads(line)
            yield idx, str(obj.get("task_id", idx)), obj.get("prompt", "")


def _select_final_code(log: dict) -> tuple[str | None, str | None]:
    """Return the latest code artifact and the log key it came from.

    Full Waterfall/QA workflows write FinalCode.  Role ablations that stop
    after the Developer stage write Code0Revise.  The remaining fallbacks make
    failures diagnosable instead of silently returning an empty result.
    """
    for key in (
        "FinalCode",
        "Code0Revise",
        "Code0",
        "Code0Draft",
        "Code0draft",
    ):
        value = log.get(key)
        if isinstance(value, str) and value.strip():
            return value, key
    return None, None


def run_one(task_id: str, prompt: str, workflow_rel: str):
    wf = Workflow()
    flow_path = HERE / "workflow" / workflow_rel
    flow = wf.loads_workflow(str(flow_path))
    workspace = wf.create_workspace(task_id=task_id)

    # Seed the raw task in the log so ablations that omit the Product Manager
    # can still start from the same task specification.
    with open(Path(workspace) / "log.json", "r", encoding="utf-8") as f:
        log = json.load(f)
    log["task"] = prompt
    log["task-id"] = task_id
    log["workflow"] = workflow_rel
    with open(Path(workspace) / "log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    step_errors = []
    for stage in flow:
        print(f"[*] Stage: {stage['stage']}")
        for step in stage["steps"]:
            print(f"[*] Step: {step['key']} | Leader: {step['leader']}")
            try:
                wf.do_step(
                    step,
                    step["leader"],
                    workspace=workspace,
                    task=prompt,
                    task_id=task_id,
                    workflow=workflow_rel,
                    entry_point="social_bias_revision",
                )
            except Exception as exc:
                # Match the behavior of the handed-over FlowGen main.py: a
                # failed downstream refinement step does not erase an earlier
                # usable code artifact.  Record the failure and continue so the
                # latest code can still be evaluated by Solar.
                msg = f"{stage['stage']}::{step['key']}: {type(exc).__name__}: {exc}"
                step_errors.append(msg)
                print(f"[FLOWGEN STEP ERROR] {msg}")
                traceback.print_exc()

    with open(Path(workspace) / "log.json", "r", encoding="utf-8") as f:
        final_log = json.load(f)
    code, source_key = _select_final_code(final_log)
    return code, source_key, workspace, step_errors


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--configuration",
        choices=sorted(CONFIGS),
        help="Named RQ3 configuration. Preferred for revision experiments.",
    )
    mode.add_argument(
        "--workflow",
        choices=sorted(WORKFLOWS),
        help="Direct workflow runner for debugging/backward compatibility.",
    )
    ap.add_argument(
        "--prompts",
        default=str(ROOT / "dataset" / "prompts.jsonl"),
        help="SocialBias-Bench prompts.jsonl",
    )
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=343)
    ap.add_argument(
        "--fairness-role",
        choices=["none", "product_manager", "architect", "developer", "qa", "all"],
        default="none",
        help="Only for direct --workflow debugging. Named configurations set this automatically.",
    )
    ap.add_argument("--run-id", required=True)
    ap.add_argument(
        "--output-root",
        default=str(ROOT / "results" / "rq3_flowgen"),
    )
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    if args.configuration:
        spec = CONFIGS[args.configuration]
        workflow_rel = spec["workflow"]
        fairness_role = spec["fairness_role"]
        experiment_group = spec["group"]
        configuration = args.configuration
        ablation = configuration if experiment_group == "role_ablation" else "none"
    else:
        workflow_name = args.workflow or "waterfall"
        workflow_rel = WORKFLOWS[workflow_name]
        fairness_role = args.fairness_role
        experiment_group = "debug"
        configuration = f"{workflow_name}__fairness_{fairness_role}"
        ablation = "none"

    if not (0 <= args.start < args.end <= 343):
        raise SystemExit("Require 0 <= --start < --end <= 343")

    output_root = Path(args.output_root)
    run_root = output_root / args.run_id
    final_dir = run_root / "final_code"
    final_dir.mkdir(parents=True, exist_ok=True)

    # UnifiedLLMAPI reads fairness configuration lazily when FlowGen key modules
    # are imported during execution.
    os.environ["FLOWGEN_FAIRNESS_ROLE"] = fairness_role
    os.environ["FLOWGEN_ABLATION"] = ablation
    os.environ["FLOWGEN_RUN_ID"] = args.run_id
    os.environ["FLOWGEN_WORKSPACE_ROOT"] = str(output_root)
    os.environ["EXPERIMENT_CONTEXT"] = f"rq3:{args.run_id}:{configuration}"

    metadata = {
        "run_id": args.run_id,
        "configuration": configuration,
        "experiment_group": experiment_group,
        "workflow_file": workflow_rel,
        "fairness_role": fairness_role,
        "ablation": ablation,
        "model": os.getenv("OPENAI_MODEL", "gpt-6-luna"),
        "reasoning_effort": os.getenv("OPENAI_REASONING_EFFORT", "none"),
        "reasoning_mode": os.getenv("OPENAI_REASONING_MODE", "standard"),
        "temperature": os.getenv("FLOWGEN_TEMPERATURE", os.getenv("REVISION_COMMON_TEMPERATURE", "0.8")),
        "benchmark_mode": os.getenv("FLOWGEN_BENCHMARK_MODE", "1"),
        "start": args.start,
        "end": args.end,
        "operationalization": (
            "Original handed-over FlowGen workflow" if experiment_group != "role_ablation" else
            "Reconstructed from manuscript role-removal definition; see docs/RQ3_ABLATION_IMPLEMENTATION.md"
        ),
    }
    with (run_root / "run_config.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    failures = 0
    for _, task_id, prompt in read_prompts(Path(args.prompts), args.start, args.end):
        out_path = final_dir / f"task_{task_id}_generated_code.jsonl"
        if out_path.exists() and not args.overwrite:
            print(f"[skip] task {task_id}: {out_path} exists")
            continue
        print(f"\n=== RQ3 {configuration} | task {task_id} ===")
        try:
            result, source_key, workspace, step_errors = run_one(task_id, prompt, workflow_rel)
            if not result:
                raise RuntimeError(
                    f"No final code artifact found in {workspace}. "
                    "Expected one of FinalCode/Code0Revise/Code0/Code0Draft."
                )
            normalized, normalize_error = normalize_generated_code(result, prompt)
            payload = {
                "generated_code": normalized if normalized is not None else result,
                "raw_generated_code": result,
                "task_id": task_id,
                "workspace": workspace,
                "source_log_key": source_key,
                "configuration": configuration,
                "flowgen_step_errors": step_errors,
                "normalization_error": normalize_error,
                "extraction_ok": normalized is not None,
            }
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
                f.write("\n")
            if normalize_error:
                print(f"[NON-EXECUTABLE OUTPUT] task {task_id}: {normalize_error}")
        except Exception as exc:
            failures += 1
            print(f"[ERROR] task {task_id}: {exc}")
            traceback.print_exc()

    print(f"\nDone. Final code: {final_dir}")
    if failures:
        print(f"Failures: {failures}. Re-run the same command to resume missing tasks.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
