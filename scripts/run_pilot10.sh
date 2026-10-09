#!/usr/bin/env bash
# Ten-task pilot over every revised condition before the full campaign.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
TAG="${1:-pilot10}"

python scripts/preflight.py

echo "===== RQ1 pilot: tasks 0-9 at common anchor 0.8, one sample ====="
python commands/run_rq1_revision.py \
  --run-id "${TAG}_rq1" --start 0 --end 10 --samples 1 --temps 0.8
bash commands/evaluate_solar.sh \
  --response-dir "results/rq1/${TAG}_rq1/temp_0.8/developer" \
  --out-dir "results/rq1/${TAG}_rq1/solar_temp_0.8" \
  --label developer --start 0 --end 10 --samples 1

echo "===== RQ2 pilot: tasks 0-9, all six conditions, one sample ====="
python commands/run_rq2_revision.py \
  --run-id "${TAG}_rq2" --start 0 --end 10 --samples 1
for cond in rq2_default rq2_cot_only rq2_fairness_only rq2_positive_role_only rq2_cot_fairness rq2_positive_cot_fairness; do
  bash commands/evaluate_solar.sh \
    --response-dir "results/rq2/${TAG}_rq2/${cond}/developer" \
    --out-dir "results/rq2/${TAG}_rq2/solar_${cond}" \
    --label developer --start 0 --end 10 --samples 1
done

echo "===== RQ3 pilot: tasks 0-9, all 12 configurations ====="
python commands/run_rq3_revision.py \
  --replicate-id "${TAG}_rq3_rep1" --start 0 --end 10 --evaluate

echo "===== RQ4 pilot: tasks 0-9, full three-round FMA ====="
python commands/run_rq4_revision.py \
  --run-id "${TAG}_rq4_rep1" --start 0 --end 10 --rounds 3 --evaluate

echo "===== Usage ====="
python scripts/summarize_usage.py

echo "===== Pilot complete ====="
