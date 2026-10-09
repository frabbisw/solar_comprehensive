#!/usr/bin/env python3
"""Run the complete RQ3 revision matrix for one independent replicate.

One replicate contains 12 unique configurations.  Re-run this command with a
new --replicate-id for replicate 2/3.  Existing task outputs are skipped, so a
failed/interrupted replicate can be resumed with the same command.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

CONFIGS = [
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


def run(cmd):
    print("\n$", " ".join(map(str, cmd)), flush=True)
    subprocess.run(list(map(str, cmd)), cwd=ROOT, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicate-id", required=True, help="e.g., luna_rq3_rep1")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=343)
    ap.add_argument("--evaluate", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--configurations", nargs="+", choices=CONFIGS, default=CONFIGS)
    args = ap.parse_args()

    for config in args.configurations:
        run_id = f"{args.replicate_id}__{config}"
        cmd = [
            PYTHON,
            ROOT / "flowgen" / "run_flowgen.py",
            "--configuration", config,
            "--start", args.start,
            "--end", args.end,
            "--run-id", run_id,
        ]
        if args.overwrite:
            cmd.append("--overwrite")
        run(cmd)

        if args.evaluate:
            run([
                ROOT / "commands" / "evaluate_solar.sh",
                "--response-dir", ROOT / "results" / "rq3_flowgen" / run_id / "final_code",
                "--out-dir", ROOT / "results" / "rq3_flowgen" / run_id / "solar",
                "--label", "final",
                "--start", args.start,
                "--end", args.end,
                "--samples", "1",
            ])

    print(f"\nRQ3 replicate complete: {args.replicate_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
