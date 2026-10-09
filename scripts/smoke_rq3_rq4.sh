#!/usr/bin/env bash
# Re-test only RQ3 and RQ4 after the FlowGen/Solar compatibility fixes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
RUN_TAG="${1:-smoke2}"

python scripts/preflight.py

echo "===== RQ3: task 0, all 12 configurations ====="
python commands/run_rq3_revision.py \
  --replicate-id "${RUN_TAG}_rq3_rep1" --start 0 --end 1 --evaluate

echo "===== RQ4: task 0, full FMA, one repair round ====="
python commands/run_rq4_revision.py \
  --run-id "${RUN_TAG}_rq4_rep1" --start 0 --end 1 --rounds 1 --evaluate

echo "===== Usage ====="
python scripts/summarize_usage.py

echo "===== RQ3/RQ4 smoke complete ====="
