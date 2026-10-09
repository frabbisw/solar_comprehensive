#!/usr/bin/env bash
# Full first-pass campaign. Long-running. The staged plan is safer because it
# lets you inspect the RQ3 pilot before launching the full RQ3 run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
TAG="${1:-luna_revision}"
python scripts/preflight.py
bash scripts/run_rq1_full.sh "${TAG}_rq1"
bash scripts/run_rq4_once.sh "${TAG}_rq4_run1"
bash scripts/run_rq3_once.sh "${TAG}_rq3_run1"
bash scripts/run_rq2_once.sh "${TAG}_rq2" "${TAG}_rq1"
python scripts/summarize_usage.py
