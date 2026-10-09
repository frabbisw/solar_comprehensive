#!/usr/bin/env bash
# Later-stage reviewer robustness run: three independent complete RQ4 executions.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PREFIX="${1:-luna_rq4}"
for rep in 1 2 3; do
  python commands/run_rq4_revision.py \
    --run-id "${PREFIX}_run${rep}" --start 0 --end 343 --rounds 3 --evaluate
done
