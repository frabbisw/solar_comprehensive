#!/usr/bin/env bash
# One complete RQ3 execution: all 12 configurations x all 343 tasks.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:-luna_rq3_run1}"
python commands/run_rq3_revision.py \
  --replicate-id "$RUN_ID" --start 0 --end 343 --evaluate
