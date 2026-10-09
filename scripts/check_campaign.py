#!/usr/bin/env python3
"""Check whether a smoke/full revision campaign has all expected task outputs.

Examples
--------
python scripts/check_campaign.py --tag luna_revision --full
python scripts/check_campaign.py --tag smoke1 --smoke

For --full, TAG corresponds to scripts/run_all_full.sh TAG, producing:
  results/rq1/<TAG>_rq1
  results/rq2/<TAG>_rq2
  results/rq3_flowgen/<TAG>_rq3_runN__CONFIG
  results/rq4/<TAG>_rq4_runN

For --smoke, TAG corresponds to scripts/smoke_all.sh TAG.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RQ2_CONDITIONS = [
    "rq2_default",
    "rq2_cot_only",
    "rq2_fairness_only",
    "rq2_positive_role_only",
    "rq2_cot_fairness",
    "rq2_positive_cot_fairness",
]
RQ3_CONFIGS = [
    "raw",
    "waterfall",
    "scrum",
    "waterfall_pm_fair",
    "waterfall_architect_fair",
    "waterfall_developer_fair",
    "waterfall_qa_fair",
    "waterfall_all_fair",
    "no_tester",
    "no_architect_tester",
    "no_requirement_tester",
    "developer_only",
]
TEMPS = ["0.2", "0.4", "0.6", "0.8", "1"]


def jsonl_count(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def code_dir_status(path: Path, start: int, end: int, samples: int) -> tuple[int, list[int], list[tuple[int,int]]]:
    present = 0
    missing: list[int] = []
    short: list[tuple[int,int]] = []
    for task in range(start, end):
        p = path / f"task_{task}_generated_code.jsonl"
        n = jsonl_count(p)
        if n == 0:
            missing.append(task)
        else:
            present += 1
            if n < samples:
                short.append((task, n))
    return present, missing, short


def solar_status(path: Path, label: str, start: int, end: int) -> tuple[int, list[int]]:
    b = path / "test_result" / label / "bias_info_files"
    ok = 0
    missing = []
    for task in range(start, end):
        p = b / f"bias_info{task}.jsonl"
        if p.exists() and p.stat().st_size > 0:
            ok += 1
        else:
            missing.append(task)
    return ok, missing


def show(name: str, expected: int, present: int, missing: list[int], short=None) -> bool:
    good = present == expected and not missing and not short
    mark = "OK" if good else "MISSING"
    print(f"[{mark:7}] {name}: {present}/{expected}")
    if missing:
        preview = ",".join(map(str, missing[:20]))
        more = " ..." if len(missing) > 20 else ""
        print(f"          missing task IDs: {preview}{more}")
    if short:
        preview = ", ".join(f"{t}({n})" for t,n in short[:20])
        more = " ..." if len(short) > 20 else ""
        print(f"          short sample files task(count): {preview}{more}")
    return good


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--reps", type=int, default=1, help="Number of full RQ3/RQ4 repetitions to check")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--full", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    start, end = (0, 343) if args.full else (0, 1)
    n_tasks = end - start
    all_good = True

    # RQ1
    rq1_id = f"{args.tag}_rq1"
    temps = TEMPS if args.full else ["0.8"]
    samples = 5 if args.full else 1
    for t in temps:
        d = ROOT / "results" / "rq1" / rq1_id / f"temp_{t}" / "developer"
        present, missing, short = code_dir_status(d, start, end, samples)
        all_good &= show(f"RQ1 temp {t} code", n_tasks, present, missing, short)
        s = ROOT / "results" / "rq1" / rq1_id / f"solar_temp_{t}"
        present, missing = solar_status(s, "developer", start, end)
        all_good &= show(f"RQ1 temp {t} Solar", n_tasks, present, missing)

    # RQ2
    rq2_id = f"{args.tag}_rq2"
    for cond in RQ2_CONDITIONS:
        d = ROOT / "results" / "rq2" / rq2_id / cond / "developer"
        present, missing, short = code_dir_status(d, start, end, samples)
        all_good &= show(f"RQ2 {cond} code", n_tasks, present, missing, short)
        s = ROOT / "results" / "rq2" / rq2_id / f"solar_{cond}"
        present, missing = solar_status(s, "developer", start, end)
        all_good &= show(f"RQ2 {cond} Solar", n_tasks, present, missing)

    # RQ3
    reps = tuple(range(1, args.reps + 1)) if args.full else (1,)
    rq3_prefix = f"{args.tag}_rq3"
    for rep in reps:
        for config in RQ3_CONFIGS:
            rid = f"{rq3_prefix}_run{rep}__{config}"
            d = ROOT / "results" / "rq3_flowgen" / rid / "final_code"
            present, missing, short = code_dir_status(d, start, end, 1)
            all_good &= show(f"RQ3 rep{rep} {config} code", n_tasks, present, missing, short)
            s = ROOT / "results" / "rq3_flowgen" / rid / "solar"
            present, missing = solar_status(s, "final", start, end)
            all_good &= show(f"RQ3 rep{rep} {config} Solar", n_tasks, present, missing)

    # RQ4
    rq4_prefix = f"{args.tag}_rq4"
    rounds = (1,2,3) if args.full else (1,)
    for rep in reps:
        rid = f"{rq4_prefix}_run{rep}"
        d = ROOT / "results" / "rq4" / rid / "developer"
        present, missing, short = code_dir_status(d, start, end, 1)
        all_good &= show(f"RQ4 rep{rep} developer code", n_tasks, present, missing, short)
        sroot = ROOT / "results" / "rq4" / rid / "solar"
        present, missing = solar_status(sroot, "developer", start, end)
        all_good &= show(f"RQ4 rep{rep} developer Solar", n_tasks, present, missing)
        for r in rounds:
            d = ROOT / "results" / "rq4" / rid / f"round{r}" / "fairness_repairer"
            present, missing, short = code_dir_status(d, start, end, 1)
            all_good &= show(f"RQ4 rep{rep} round{r} code", n_tasks, present, missing, short)
            present, missing = solar_status(sroot, f"round{r}", start, end)
            all_good &= show(f"RQ4 rep{rep} round{r} Solar", n_tasks, present, missing)

    print("\nCampaign completeness:", "PASS" if all_good else "INCOMPLETE")
    return 0 if all_good else 1


if __name__ == "__main__":
    raise SystemExit(main())
