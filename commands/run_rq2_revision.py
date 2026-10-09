#!/usr/bin/env python3
"""Run the rebuttal RQ2 prompt-disentanglement conditions.

When --default-source-dir is supplied, RQ2 Default is copied from the already
completed RQ1 t=0.8 default condition.  This avoids paying for duplicate model
calls while preserving an identical Luna baseline across RQ1 and RQ2.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
DEFAULT_CONDITIONS=[
    'rq2_default','rq2_cot_only','rq2_fairness_only','rq2_positive_role_only',
    'rq2_cot_fairness','rq2_positive_cot_fairness'
]


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open('r', encoding='utf-8') as f:
        return sum(1 for line in f if line.strip())


def reuse_default(source: Path, dest: Path, start: int, end: int, samples: int) -> None:
    if not source.is_dir():
        raise SystemExit(f'RQ1 default source directory not found: {source}')
    dest.mkdir(parents=True, exist_ok=True)
    missing=[]
    for task_id in range(start, end):
        src=source/f'task_{task_id}_generated_code.jsonl'
        n=_count_jsonl(src)
        if n < samples:
            missing.append((task_id,n))
            continue
        dst=dest/f'task_{task_id}_generated_code.jsonl'
        if _count_jsonl(dst) >= samples:
            continue
        # RQ1 should contain exactly five samples, but slice defensively so the
        # RQ2 condition always contains exactly --samples records.
        lines=[ln for ln in src.read_text(encoding='utf-8').splitlines() if ln.strip()][:samples]
        dst.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    if missing:
        preview=', '.join(f'{tid}({n}/{samples})' for tid,n in missing[:10])
        raise SystemExit(
            f'RQ1 t=0.8 is incomplete for {len(missing)} task(s); examples: {preview}. '
            'Finish RQ1 before reusing it as RQ2 Default.'
        )
    meta={
        'condition':'rq2_default',
        'reused_from':str(source.resolve()),
        'start':start,'end':end,'samples_per_task':samples,
        'note':'Identical Luna default outputs reused from RQ1 temperature 0.8; no new API calls.'
    }
    (dest.parent/'_reuse_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(f'[RQ2] Reused Default from RQ1: {source} -> {dest}', flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--end', type=int, default=343)
    ap.add_argument('--samples', type=int, default=5)
    ap.add_argument('--temperature', type=float, default=float(os.getenv('REVISION_COMMON_TEMPERATURE','0.8')))
    ap.add_argument('--conditions', nargs='+', default=DEFAULT_CONDITIONS)
    ap.add_argument('--default-source-dir', default='', help='Optional RQ1 t=0.8 developer output directory to reuse for rq2_default')
    args=ap.parse_args()
    prompts=ROOT/'dataset'/'prompts.jsonl'
    for cond in args.conditions:
        os.environ['EXPERIMENT_CONTEXT'] = f'rq2:{args.run_id}:{cond}'
        out=ROOT/'results'/'rq2'/args.run_id/cond/'developer'
        if cond == 'rq2_default' and args.default_source_dir:
            source=Path(args.default_source_dir)
            if not source.is_absolute():
                source=ROOT/source
            reuse_default(source,out,args.start,args.end,args.samples)
            continue
        out.mkdir(parents=True,exist_ok=True)
        cmd=[sys.executable,str(ROOT/'agents'/'developer.py'),
             '--prompts_file',str(prompts),'--model','gpt','--prompt_style',cond,
             '--temperature',str(args.temperature),'--num_samples',str(args.samples),
             '--start',str(args.start),'--end',str(args.end),'--output_dir',str(out)]
        print('\n$', ' '.join(cmd), flush=True)
        subprocess.run(cmd,cwd=ROOT,check=True)
    return 0

if __name__=='__main__': raise SystemExit(main())
