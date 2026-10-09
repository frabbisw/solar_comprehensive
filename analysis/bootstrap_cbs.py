#!/usr/bin/env python3
"""Cluster-bootstrap CBS confidence intervals across repeated runs.

Examples
--------
# RQ4 developer -> round3 paired reduction across three replicates
python analysis/bootstrap_cbs.py \
  --roots results/rq4/luna_revision_rq4_rep1/solar \
          results/rq4/luna_revision_rq4_rep2/solar \
          results/rq4/luna_revision_rq4_rep3/solar \
  --agent round3 --before-agent developer

# One RQ3 configuration across three replicates
python analysis/bootstrap_cbs.py \
  --roots results/rq3_flowgen/luna_revision_rq3_rep1__waterfall/solar \
          results/rq3_flowgen/luna_revision_rq3_rep2__waterfall/solar \
          results/rq3_flowgen/luna_revision_rq3_rep3__waterfall/solar \
  --agent final

The bootstrap resamples task IDs, keeping all replicates for a sampled task
together. This respects the repeated-run structure better than treating every
run-task pair as independent.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def load_status(root: Path, agent: str, start: int, end: int) -> dict[int, float | None]:
    out = {}
    base = root / "test_result" / agent / "bias_info_files"
    for task in range(start, end):
        p = base / f"bias_info{task}.jsonl"
        if not p.exists():
            out[task] = None
            continue
        lines = [x for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        if not lines:
            out[task] = None
            continue
        obj = json.loads(lines[0])
        val = str(obj.get("bias_info", "failed")).strip().lower()
        if val == "failed":
            out[task] = None
        else:
            out[task] = 0.0 if val in {"", "none"} else 1.0
    return out


def mean_valid(vals):
    xs = [x for x in vals if x is not None]
    return sum(xs) / len(xs) if xs else None


def percentile(xs, q):
    if not xs:
        return float("nan")
    ys = sorted(xs)
    pos = (len(ys) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ys) - 1)
    frac = pos - lo
    return ys[lo] * (1 - frac) + ys[hi] * frac


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", required=True, help="Solar output roots, one per replicate")
    ap.add_argument("--agent", required=True, help="e.g. final or round3")
    ap.add_argument("--before-agent", default="", help="Optional paired baseline agent, e.g. developer")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=343)
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20261003)
    args = ap.parse_args()

    roots = [Path(x) for x in args.roots]
    after = [load_status(r, args.agent, args.start, args.end) for r in roots]
    before = [load_status(r, args.before_agent, args.start, args.end) for r in roots] if args.before_agent else None
    tasks = list(range(args.start, args.end))

    def stage_cbs(maps, sample_tasks=tasks):
        per_task = []
        for t in sample_tasks:
            v = mean_valid([m.get(t) for m in maps])
            if v is not None:
                per_task.append(v)
        return sum(per_task) / len(per_task) if per_task else float("nan")

    point_after = stage_cbs(after)
    point_before = stage_cbs(before) if before else None

    rng = random.Random(args.seed)
    boot_after = []
    boot_before = []
    boot_reduction = []
    for _ in range(args.bootstrap):
        sample = [rng.choice(tasks) for _ in tasks]
        a = stage_cbs(after, sample)
        boot_after.append(a)
        if before:
            b = stage_cbs(before, sample)
            boot_before.append(b)
            if b > 0:
                boot_reduction.append((b - a) / b)

    def report(name, point, boots):
        lo, hi = percentile(boots, 0.025), percentile(boots, 0.975)
        print(f"{name}: {point*100:.2f}%  95% bootstrap CI [{lo*100:.2f}%, {hi*100:.2f}%]")

    print(f"Replicates: {len(roots)} | tasks: {args.start}-{args.end-1} | bootstrap: {args.bootstrap}")
    report(args.agent, point_after, boot_after)
    if before:
        report(args.before_agent, point_before, boot_before)
        reduction = (point_before - point_after) / point_before if point_before and point_before > 0 else float("nan")
        lo, hi = percentile(boot_reduction, 0.025), percentile(boot_reduction, 0.975)
        print(f"Relative CBS reduction ({args.before_agent} -> {args.agent}): {reduction*100:.2f}%  95% CI [{lo*100:.2f}%, {hi*100:.2f}%]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
