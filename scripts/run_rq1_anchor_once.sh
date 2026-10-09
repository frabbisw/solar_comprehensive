#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:-luna_rq1_run1}"
TEMP="${2:-${REVISION_COMMON_TEMPERATURE:-0.8}}"

python commands/run_rq1_revision.py \
  --run-id "$RUN_ID" --start 0 --end 343 --samples 5 --temps "$TEMP"

TDIR="${TEMP%0}"; TDIR="${TDIR%.}"
bash commands/evaluate_solar.sh \
  --response-dir "results/rq1/$RUN_ID/temp_${TDIR}/developer" \
  --out-dir "results/rq1/$RUN_ID/solar_temp_${TDIR}" \
  --label developer --start 0 --end 343 --samples 5

printf '\nRQ1 anchor run complete: %s at temperature %s (343 tasks x 5 samples)\n' "$RUN_ID" "$TEMP"
