#!/usr/bin/env bash
# Later-stage reviewer robustness run: three independent complete RQ3 executions.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PREFIX="${1:-luna_rq3}"
for rep in 1 2 3; do
  python commands/run_rq3_revision.py \
    --replicate-id "${PREFIX}_run${rep}" --start 0 --end 343 --evaluate
done
