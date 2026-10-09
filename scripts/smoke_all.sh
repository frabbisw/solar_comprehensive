#!/usr/bin/env bash
# One-task end-to-end smoke test for every revised experiment condition.
# This intentionally exercises all 12 RQ3 configurations, including the four
# reconstructed role ablations, before any full 343-task campaign is launched.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
RUN_TAG="${1:-smoke}"

python scripts/preflight.py

if [[ -z "${OPENAI_API_KEY:-}" && ! -f .env ]]; then
  echo "OPENAI_API_KEY is not available. Create .env from .env.example first." >&2
  exit 2
fi

echo "===== RQ1: task 0, common anchor temperature 0.8 ====="
python commands/run_rq1_revision.py \
  --run-id "${RUN_TAG}_rq1" --start 0 --end 1 --samples 1 --temps 0.8
bash commands/evaluate_solar.sh \
  --response-dir "results/rq1/${RUN_TAG}_rq1/temp_0.8/developer" \
  --out-dir "results/rq1/${RUN_TAG}_rq1/solar_temp_0.8" \
  --label developer --start 0 --end 1 --samples 1

echo "===== RQ2: task 0, all six prompt conditions ====="
python commands/run_rq2_revision.py \
  --run-id "${RUN_TAG}_rq2" --start 0 --end 1 --samples 1
for cond in rq2_default rq2_cot_only rq2_fairness_only rq2_positive_role_only rq2_cot_fairness rq2_positive_cot_fairness; do
  bash commands/evaluate_solar.sh \
    --response-dir "results/rq2/${RUN_TAG}_rq2/${cond}/developer" \
    --out-dir "results/rq2/${RUN_TAG}_rq2/solar_${cond}" \
    --label developer --start 0 --end 1 --samples 1
done

echo "===== RQ3: task 0, all 12 configurations ====="
python commands/run_rq3_revision.py \
  --replicate-id "${RUN_TAG}_rq3_rep1" --start 0 --end 1 --evaluate

echo "===== RQ4: task 0, full FMA, one repair round ====="
python commands/run_rq4_revision.py \
  --run-id "${RUN_TAG}_rq4_rep1" --start 0 --end 1 --rounds 1 --evaluate

echo "===== Usage ====="
python scripts/summarize_usage.py

echo "===== Smoke suite complete ====="
