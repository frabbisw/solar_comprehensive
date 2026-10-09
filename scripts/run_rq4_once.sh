#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:-luna_rq4_run1}"
python commands/run_rq4_revision.py \
  --run-id "$RUN_ID" --start 0 --end 343 --rounds 3 --evaluate
