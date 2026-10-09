#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:-luna_rq1}"
python commands/run_rq1_revision.py \
  --run-id "$RUN_ID" --start 0 --end 343 --samples 5 \
  --temps 0.2 0.4 0.6 0.8 1.0 --style default
for t in 0.2 0.4 0.6 0.8 1.0; do
  tdir="${t%0}"; tdir="${tdir%.}"
  bash commands/evaluate_solar.sh \
    --response-dir "results/rq1/$RUN_ID/temp_${tdir}/developer" \
    --out-dir "results/rq1/$RUN_ID/solar_temp_${tdir}" \
    --label developer --start 0 --end 343 --samples 5
done
