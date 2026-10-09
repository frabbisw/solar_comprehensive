#!/usr/bin/env python3
"""Run the GPT replacement arm for RQ1 (temperature sensitivity)."""
from __future__ import annotations
import argparse, os, subprocess, sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--end', type=int, default=343)
    ap.add_argument('--samples', type=int, default=5)
    ap.add_argument('--temps', nargs='+', type=float, default=[0.2,0.4,0.6,0.8,1.0])
    ap.add_argument('--style', default='default')
    args=ap.parse_args()

    effort=os.getenv('OPENAI_REASONING_EFFORT','none').lower()
    if effort != 'none' and len(args.temps) > 1:
        raise SystemExit(
            'RQ1 temperature sweep is invalid with GPT-6 reasoning enabled. '
            'Set OPENAI_REASONING_EFFORT=none, or run only one fixed condition.'
        )

    prompts=ROOT/'dataset'/'prompts.jsonl'
    for t in args.temps:
        os.environ["EXPERIMENT_CONTEXT"] = f"rq1:{args.run_id}:temp_{t:g}"
        out=ROOT/'results'/'rq1'/args.run_id/f'temp_{t:g}'/'developer'
        out.mkdir(parents=True, exist_ok=True)
        cmd=[sys.executable, str(ROOT/'agents'/'developer.py'),
             '--prompts_file',str(prompts),'--model','gpt','--prompt_style',args.style,
             '--temperature',str(t),'--num_samples',str(args.samples),
             '--start',str(args.start),'--end',str(args.end),'--output_dir',str(out)]
        print('\n$', ' '.join(cmd), flush=True)
        subprocess.run(cmd,cwd=ROOT,check=True)
    return 0

if __name__=='__main__': raise SystemExit(main())
