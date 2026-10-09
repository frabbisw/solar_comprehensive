#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
RUN_ID="${1:-luna_rq2_run1}"
RQ1_RUN_ID="${2:-luna_rq1_run1}"
DEFAULT_SOURCE="results/rq1/$RQ1_RUN_ID/temp_0.8/developer"

python commands/run_rq2_revision.py \
  --run-id "$RUN_ID" --start 0 --end 343 --samples 5 \
  --temperature "${REVISION_COMMON_TEMPERATURE:-0.8}" \
  --default-source-dir "$DEFAULT_SOURCE"

for cond in rq2_default rq2_cot_only rq2_fairness_only rq2_positive_role_only rq2_cot_fairness rq2_positive_cot_fairness; do
  bash commands/evaluate_solar.sh \
    --response-dir "results/rq2/$RUN_ID/$cond/developer" \
    --out-dir "results/rq2/$RUN_ID/solar_$cond" \
    --label developer --start 0 --end 343 --samples 5
done

printf '\nRQ2 Luna run complete: %s\n' "$RUN_ID"
printf 'Default reused from RQ1: %s at t=0.8\n' "$RQ1_RUN_ID"
printf 'New API generations: 343 x 5 samples x 5 additional styles = 8,575\n'
