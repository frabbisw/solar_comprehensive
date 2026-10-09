#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:-luna_rq3_pilot5_run1}"
N="${2:-5}"
if ! [[ "$N" =~ ^[0-9]+$ ]] || (( N < 1 || N > 343 )); then
  echo "N must be an integer in 1..343" >&2
  exit 2
fi
python commands/run_rq3_revision.py \
  --replicate-id "$RUN_ID" --start 0 --end "$N" --evaluate
