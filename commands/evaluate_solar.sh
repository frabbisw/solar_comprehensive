#!/usr/bin/env bash
# Evaluate an existing generated-code directory with Solar for a task range.
set -euo pipefail
RESP_DIR=""; OUT_DIR=""; LABEL="run"; START=0; END=343; SAMPLES=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --response-dir) RESP_DIR="$2"; shift 2;;
    --out-dir) OUT_DIR="$2"; shift 2;;
    --label) LABEL="$2"; shift 2;;
    --start) START="$2"; shift 2;;
    --end) END="$2"; shift 2;;
    --samples) SAMPLES="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done
[[ -n "$RESP_DIR" && -n "$OUT_DIR" ]] || { echo "Need --response-dir and --out-dir" >&2; exit 2; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOLAR="$ROOT/fairness_test"
RESP_DIR="$(realpath "$RESP_DIR")"
mkdir -p "$OUT_DIR"; OUT_DIR="$(realpath "$OUT_DIR")"
LABEL_DIR="$OUT_DIR/test_result/$LABEL"
# Solar is deterministic for a fixed generated-code directory. Rebuild this
# label from scratch on every evaluation so rerunning after an interruption
# cannot append duplicate CSV log entries.
rm -rf "$LABEL_DIR"
LOG_DIR="$LABEL_DIR/log_files"
REPORT_DIR="$LABEL_DIR/inconsistency_files"
BIAS_DIR="$LABEL_DIR/bias_info_files"
mkdir -p "$LOG_DIR" "$REPORT_DIR" "$BIAS_DIR"
cd "$SOLAR/test_suites"
cp config_template.py config.py
python - "$RESP_DIR" "$LOG_DIR" "$REPORT_DIR" <<'PY'
import sys
p='config.py'
s=open(p).read().replace('##PATH##TO##RESPONSE##',sys.argv[1]).replace('##PATH##TO##LOG##FILES##',sys.argv[2]).replace('##PATH##TO##INCONSISTENCY##FILES##',sys.argv[3])
open(p,'w').write(s)
PY
TEST_FILES=()
for ((i=START;i<END;i++)); do [[ -f "test_suite_${i}.py" ]] && TEST_FILES+=("test_suite_${i}.py"); done
pytest "${TEST_FILES[@]}"
cd "$ROOT"
python "$SOLAR/parse_bias_info.py" "$LOG_DIR" "$BIAS_DIR" "$SAMPLES"
cd "$SOLAR"
python summary_result.py "$OUT_DIR" "$START" "$END" "$LABEL" || true
python count_bias.py "$OUT_DIR" "$START" "$END" "$LABEL" || true
python count_bias_leaning.py "$OUT_DIR" "$START" "$END" "$LABEL" || true
python count_related.py "$OUT_DIR" "$START" "$END" "$LABEL" || true
cd "$ROOT"
python score/calculate_scores.py \
  --model_dir "$OUT_DIR" --agent "$LABEL" --start "$START" --end "$END" --samples "$SAMPLES" || true

# The raw Solar CSVs can be enormous (especially inconsistency_files) and are
# fully reproducible from the saved generated code.  Keep the compact derived
# artifacts used by the paper (bias/related JSONL, summaries, aggregate JSON,
# scores) and prune raw test artifacts by default.  Set SOLAR_KEEP_RAW=1 only
# when debugging a specific evaluation.
if [[ "${SOLAR_KEEP_RAW:-0}" != "1" ]]; then
  rm -rf "$LOG_DIR" "$REPORT_DIR"
  printf 'Pruned raw Solar artifacts: %s and %s\n' "$LOG_DIR" "$REPORT_DIR"
fi

printf '\nSolar output: %s\n' "$OUT_DIR/test_result/$LABEL"
