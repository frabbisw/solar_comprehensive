#!/usr/bin/env python3
"""RQ4 runner matching the manuscript's FMA architecture.

Pipeline per task/run:
  Functional Requirements Analyst
  -> Fairness Requirements Analyst
  -> Developer
  -> [Functional Reviewer -> Functional Repairer
      -> Fairness Reviewer -> Fairness Repairer] x N rounds

Solar is external and optional; its outputs are never supplied to any agent.
Use one sample per task and repeat the whole run with different --run-id values
for stochastic replication.
"""
from __future__ import annotations

import argparse
import os
from dotenv import load_dotenv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
PY = sys.executable


def run(cmd):
    print('\n$', ' '.join(map(str, cmd)), flush=True)
    subprocess.run(list(map(str, cmd)), cwd=ROOT, check=True)


def common(prompts, start, end, temp, samples=1):
    return [
        '--prompts_file', prompts, '--model', 'gpt', '--temperature', str(temp),
        '--num_samples', str(samples), '--start', str(start), '--end', str(end),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--end', type=int, default=343)
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--temperature', type=float, default=float(os.getenv('REVISION_COMMON_TEMPERATURE', '0.8')))
    ap.add_argument('--evaluate', action='store_true')
    ap.add_argument(
        '--post-developer-only',
        action='store_true',
        help='Reuse existing requirements/developer outputs and run only the post-Developer loop',
    )
    args = ap.parse_args()
    if not (1 <= args.rounds <= 3):
        raise SystemExit('--rounds must be 1..3')

    os.environ['EXPERIMENT_CONTEXT'] = f"rq4:{args.run_id}"
    prompts = str(ROOT / 'dataset' / 'prompts.jsonl')
    base = ROOT / 'results' / 'rq4' / args.run_id
    func_spec = base / 'functional_requirements'
    fair_spec = base / 'fairness_requirements'
    developer = base / 'developer'

    if args.post_developer_only:
        missing = [p for p in (func_spec, fair_spec, developer) if not p.is_dir()]
        if missing:
            raise SystemExit(f'--post-developer-only requires existing upstream directories: {missing}')
    else:
        for p in (func_spec, fair_spec, developer):
            p.mkdir(parents=True, exist_ok=True)

    c = common(prompts, args.start, args.end, args.temperature, 1)

    if not args.post_developer_only:
        run([PY, ROOT/'agents_full'/'requirements.py', *c, '--output_dir', func_spec])
        run([PY, ROOT/'fma_full'/'bias_aware_requirements.py', *c,
             '--prd_dir', func_spec, '--output_dir', fair_spec])
        run([PY, ROOT/'agents_full'/'developer.py', *c, '--prompt_style', 'agent',
             '--spec_dir', fair_spec, '--output_dir', developer])

    if args.evaluate:
        run([ROOT/'commands'/'evaluate_solar.sh', '--response-dir', developer,
             '--out-dir', base/'solar', '--label', 'developer', '--start', args.start,
             '--end', args.end, '--samples', '1'])

    current = developer
    for r in range(1, args.rounds + 1):
        func_rev = base/f'round{r}'/'functional_reviewer'
        func_rep = base/f'round{r}'/'functional_repairer'
        fair_rev = base/f'round{r}'/'fairness_reviewer'
        fair_rep = base/f'round{r}'/'fairness_repairer'
        for p in (func_rev, func_rep, fair_rev, fair_rep):
            p.mkdir(parents=True, exist_ok=True)

        run([PY, ROOT/'agents_full'/'reviewer.py', *c,
             '--code_dir', current, '--spec_dir', func_spec, '--output_dir', func_rev])
        run([PY, ROOT/'agents_full'/'repairer.py', *c,
             '--code_dir', current, '--review_dir', func_rev,
             '--spec_dir', func_spec, '--output_dir', func_rep])
        run([PY, ROOT/'fma_full'/'bias_aware_reviewer.py', *c,
             '--code_dir', func_rep, '--spec_dir', fair_spec, '--output_dir', fair_rev])
        run([PY, ROOT/'fma_full'/'bias_repairer.py', *c,
             '--code_dir', func_rep, '--review_dir', fair_rev,
             '--spec_dir', fair_spec, '--output_dir', fair_rep, '--num_rounds', '1'])

        if args.evaluate:
            run([ROOT/'commands'/'evaluate_solar.sh', '--response-dir', fair_rep,
                 '--out-dir', base/'solar', '--label', f'round{r}', '--start', args.start,
                 '--end', args.end, '--samples', '1'])
        current = fair_rep

    print(f'\nRQ4 run complete: {base}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
