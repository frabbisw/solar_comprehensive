#!/usr/bin/env python3
"""Recover provider-rejected RQ2 samples without changing the benchmark prompt.

The script scans an existing RQ2 run, snapshots every current provider rejection
into an audit JSONL, then retries only those missing model generations with the
*identical* system prompt, task prompt, temperature, and model configuration.
Successful responses replace the provider_rejected slot at the same sample index.
Unresolved provider rejections remain in place for a later rerun.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == "commands" else Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.developer import PROMPT_STYLES  # noqa: E402
from shared.io_utils import clean_code, read_jsonl_list, write_jsonl  # noqa: E402
from shared.llm_client import PromptRejectedError, chat  # noqa: E402

STYLE_DIRS = [
    "rq2_default",
    "rq2_cot_only",
    "rq2_fairness_only",
    "rq2_positive_role_only",
    "rq2_cot_fairness",
    "rq2_positive_cot_fairness",
]

TASK_RE = re.compile(r"task_(.+?)_generated_code\.jsonl$")


def load_prompts(path: Path) -> dict[str, str]:
    prompts: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            obj = json.loads(line)
            task_id = str(obj.get("task_id", idx))
            prompt = str(obj.get("prompt", "")).strip()
            if prompt:
                prompts[task_id] = prompt
    return prompts


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write("\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="luna_rq2_run1")
    ap.add_argument("--results-root", default="results/rq2")
    ap.add_argument("--prompts-file", default="dataset/prompts.jsonl")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--max-attempts-per-slot", type=int, default=10)
    args = ap.parse_args()

    run_dir = ROOT / args.results_root / args.run_id
    prompts = load_prompts(ROOT / args.prompts_file)
    audit = run_dir / "provider_rejection_recovery_audit.jsonl"
    snapshot = run_dir / "provider_rejections_before_recovery.jsonl"

    targets: list[tuple[str, str, Path, int, dict]] = []
    for style in STYLE_DIRS:
        d = run_dir / style / "developer"
        if not d.exists():
            continue
        for f in sorted(d.glob("task_*_generated_code.jsonl")):
            m = TASK_RE.search(f.name)
            if not m:
                continue
            task_id = m.group(1)
            records = read_jsonl_list(str(f))
            for pos, rec in enumerate(records):
                if rec.get("generation_status") == "provider_rejected":
                    sample_index = int(rec.get("sample_index", pos))
                    targets.append((style, task_id, f, pos, rec))

    print(f"Found {len(targets)} provider-rejected sample slots.")
    if not targets:
        return 0

    # Snapshot exactly what existed before any replacement. Do this only once,
    # so repeated recovery runs do not overwrite the original rejection set.
    if not snapshot.exists():
        with snapshot.open("w", encoding="utf-8") as out:
            for style, task_id, f, pos, rec in targets:
                row = {
                    "style": style,
                    "task_id": task_id,
                    "sample_index": int(rec.get("sample_index", pos)),
                    "original_record": rec,
                    "source_file": str(f.relative_to(ROOT)),
                }
                json.dump(row, out, ensure_ascii=False)
                out.write("\n")
        print(f"Saved original rejection snapshot: {snapshot}")
    else:
        print(f"Keeping existing original rejection snapshot: {snapshot}")

    resolved = 0
    unresolved = 0

    # Group edits by file so each JSONL is rewritten only after its slots are processed.
    by_file: dict[Path, list[tuple[str, str, int, dict]]] = {}
    for style, task_id, f, pos, rec in targets:
        by_file.setdefault(f, []).append((style, task_id, pos, rec))

    for f, slots in by_file.items():
        records = read_jsonl_list(str(f))
        file_changed = False

        for style, task_id, pos, rec in slots:
            if task_id not in prompts:
                raise RuntimeError(f"Prompt not found for task {task_id}")

            system = PROMPT_STYLES["gpt"][style]
            user_msg = f"TASK:\n{prompts[task_id]}"
            sample_index = int(rec.get("sample_index", pos))

            success = False
            rejection_count = 0
            for attempt in range(1, args.max_attempts_per_slot + 1):
                try:
                    raw = chat(
                        system,
                        user_msg,
                        model="gpt",
                        temperature=args.temperature,
                    )
                    code = clean_code(raw)
                    records[pos] = {
                        "generated_code": code,
                        "generation_status": "ok_after_provider_retry",
                        "sample_index": sample_index,
                        "provider_rejections_before_success": 1 + rejection_count,
                    }
                    append_jsonl(audit, {
                        "style": style,
                        "task_id": task_id,
                        "sample_index": sample_index,
                        "event": "recovered",
                        "retry_attempt": attempt,
                        "additional_provider_rejections": rejection_count,
                    })
                    print(
                        f"[RECOVERED] {style} task {task_id} sample {sample_index + 1}/5 "
                        f"on retry attempt {attempt}"
                    )
                    resolved += 1
                    file_changed = True
                    success = True
                    break
                except PromptRejectedError as exc:
                    rejection_count += 1
                    append_jsonl(audit, {
                        "style": style,
                        "task_id": task_id,
                        "sample_index": sample_index,
                        "event": "provider_rejected_again",
                        "retry_attempt": attempt,
                        "code": exc.code,
                    })
                    print(
                        f"[REJECTED AGAIN] {style} task {task_id} sample {sample_index + 1}/5 "
                        f"attempt {attempt}/{args.max_attempts_per_slot}"
                    )

            if not success:
                unresolved += 1
                append_jsonl(audit, {
                    "style": style,
                    "task_id": task_id,
                    "sample_index": sample_index,
                    "event": "unresolved",
                    "attempts": args.max_attempts_per_slot,
                })

        if file_changed:
            write_jsonl(str(f), records)

    print(f"\nRecovery complete: resolved={resolved}, unresolved={unresolved}")
    print(f"Audit: {audit}")
    print(f"Original rejection snapshot: {snapshot}")
    return 0 if unresolved == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
