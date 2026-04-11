#!/usr/bin/env bash
# =============================================================================
# commands/run_pipeline.sh
#
# Usage:
#   bash commands/run_pipeline.sh --exp <1|2|3> [options]
#
# Options:
#   --exp        1, 2, or 3                         (required)
#   --style      default | chain_of_thoughts |
#                positive_chain_of_thoughts | agent  (default varies by exp)
#   --samples    code samples per task               (default: 5)
#   --temp       developer temperature               (default: 1.0)
#   --model      gpt                                 (default: gpt)
#   --start      first task index inclusive          (default: 0)
#   --end        last task index exclusive           (default: 343)
#   --rounds     reviewer+repairer iterations [Exp 3] (default: 1, max: 3)
#   --solar_dir  Solar fairness_test/ directory     (required Exp 2+3)
#   --model_dir  Solar results directory            (required Exp 2+3)
#
# Model version is configured in .env: OPENAI_MODEL=gpt-3.5-turbo
#
# Examples:
#   bash commands/run_pipeline.sh --exp 1 --style default
#
#   bash commands/run_pipeline.sh --exp 3 --start 0 --end 2 --samples 1 --rounds 2 \
#       --solar_dir ~/solar_comprehensive/fairness_test \
#       --model_dir ~/solar_comprehensive/results/gpt35
# =============================================================================

set -euo pipefail

EXP=""
STYLE=""
SAMPLES=5
TEMP=1.0
MODEL="gpt"
START=0
END=343
ROUNDS=1
SOLAR_DIR=""
MODEL_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      grep '^#' "$0" | grep -v '^#!/' | sed 's/^# \{0,2\}//'; exit 0 ;;
    --exp)       EXP="$2";       shift 2 ;;
    --style)     STYLE="$2";     shift 2 ;;
    --samples)   SAMPLES="$2";   shift 2 ;;
    --temp)      TEMP="$2";      shift 2 ;;
    --model)     MODEL="$2";     shift 2 ;;
    --start)     START="$2";     shift 2 ;;
    --end)       END="$2";       shift 2 ;;
    --rounds)    ROUNDS="$2";    shift 2 ;;
    --solar_dir) SOLAR_DIR="$2"; shift 2 ;;
    --model_dir) MODEL_DIR="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$EXP" ]] && { echo "ERROR: --exp is required" >&2; exit 1; }

REPO="$(cd "$(dirname "$0")/.." && pwd)"
AGENTS="$REPO/agents"
FMA="$REPO/fma"
PROMPTS="$REPO/dataset/prompts.jsonl"
[[ -f "$PROMPTS" ]] || { echo "ERROR: prompts not found: $PROMPTS" >&2; exit 1; }

SEP="================================================================"
log_stage() {
  echo ""
  echo "$SEP"
  printf "  STAGE: %s\n  IN:    %s\n  OUT:   %s\n" "$1" "$2" "$3"
  echo "$SEP"
}

require_solar() {
  [[ -z "$SOLAR_DIR" ]] && { echo "ERROR: --solar_dir required for Exp $EXP" >&2; exit 1; }
  [[ -z "$MODEL_DIR" ]] && { echo "ERROR: --model_dir required for Exp $EXP" >&2; exit 1; }
  [[ -d "$SOLAR_DIR" ]] || { echo "ERROR: solar_dir not found: $SOLAR_DIR" >&2; exit 1; }
}

run_solar() {
  local agent="$1"
  local resp_dir="$2"
  local log_dir="$MODEL_DIR/test_result/$agent/log_files"
  local report_dir="$MODEL_DIR/test_result/$agent/inconsistency_files"
  local bias_dir="$MODEL_DIR/test_result/$agent/bias_info_files"
  echo ""; echo "$SEP"
  echo "  SOLAR: $agent"
  echo "$SEP"
  mkdir -p "$log_dir" "$report_dir" "$bias_dir"
  cd "$SOLAR_DIR/test_suites" || { echo "ERROR: cannot cd to $SOLAR_DIR/test_suites" >&2; exit 1; }
  cp config_template.py config.py
  sed -i "s|##PATH##TO##RESPONSE##|$resp_dir|g"               config.py
  sed -i "s|##PATH##TO##LOG##FILES##|$log_dir|g"               config.py
  sed -i "s|##PATH##TO##INCONSISTENCY##FILES##|$report_dir|g"  config.py
  pytest
  cd "$REPO"
  python "$SOLAR_DIR/parse_bias_info.py" "$log_dir" "$bias_dir" "$SAMPLES"

  # V2 related_info: corrected detection (outputs SAME = attr ignored)
  local log_dir_v2="${log_dir}_v2"
  local related_v2_dir="$MODEL_DIR/test_result/$agent/related_info_v2_files"
  if [[ -d "$log_dir_v2" ]]; then
    python "$SOLAR_DIR/parse_bias_info.py" "$log_dir_v2" "$related_v2_dir" "$SAMPLES"
  fi

  cd "$SOLAR_DIR"
  python summary_result.py     "$MODEL_DIR" "$START" "$END" "$agent"
  python count_bias.py         "$MODEL_DIR" "$START" "$END" "$agent"
  python count_bias_leaning.py "$MODEL_DIR" "$START" "$END" "$agent"
  python count_related.py      "$MODEL_DIR" "$START" "$END" "$agent"
  cd "$REPO"
  echo "  Done: $MODEL_DIR/test_result/$agent/"
}

bias_dir()    { echo "$MODEL_DIR/test_result/${1}/bias_info_files"; }
related_dir() { echo "$MODEL_DIR/test_result/${1}/related_info_files"; }

COMMON=(
  --prompts_file "$PROMPTS"
  --model        "$MODEL"
  --temperature  "$TEMP"
  --num_samples  "$SAMPLES"
  --start        "$START"
  --end          "$END"
)

# =============================================================================
# Experiment 1
# =============================================================================
if [[ "$EXP" == "1" ]]; then
  [[ -z "$STYLE" ]] && STYLE="default"
  DEV_OUT="$REPO/results/exp1_${STYLE}/developer"
  mkdir -p "$DEV_OUT"
  echo "$SEP"
  echo "  EXP 1 – $STYLE  model=$MODEL  tasks=$START-$END"
  echo "$SEP"
  log_stage "Developer" "$PROMPTS" "$DEV_OUT"
  python "$AGENTS/developer.py" "${COMMON[@]}" \
    --prompt_style "$STYLE" \
    --output_dir   "$DEV_OUT"
  echo ""
  echo "  Done. Feed Solar: $DEV_OUT"
fi

# =============================================================================
# Experiment 2
# =============================================================================
if [[ "$EXP" == "2" ]]; then
  [[ -z "$STYLE" ]] && STYLE="agent"
  require_solar
  BASE="$REPO/results/exp2_flowgen"
  DEV_OUT="$BASE/developer"
  REV_OUT="$BASE/reviewer"
  REP_OUT="$BASE/repairer"
  REP_V1_OUT="$BASE/repairer_v1"
  mkdir -p "$DEV_OUT" "$REV_OUT" "$REP_OUT" "$REP_V1_OUT"
  echo "$SEP"
  echo "  EXP 2 – FlowGen  model=$MODEL  tasks=$START-$END"
  echo "$SEP"

  log_stage "1  Developer" "$PROMPTS" "$DEV_OUT"
  python "$AGENTS/developer.py" "${COMMON[@]}" \
    --prompt_style "$STYLE" \
    --output_dir   "$DEV_OUT"

  run_solar "developer" "$DEV_OUT"

  log_stage "2  Reviewer" "$DEV_OUT" "$REV_OUT"
  python "$AGENTS/reviewer.py" \
    --prompts_file "$PROMPTS" \
    --code_dir     "$DEV_OUT" \
    --output_dir   "$REV_OUT" \
    --model        "$MODEL" \
    --temperature  0.0 \
    --num_samples  "$SAMPLES" \
    --start        "$START" \
    --end          "$END"

  log_stage "3a  Repairer v2" "$DEV_OUT + $REV_OUT" "$REP_OUT"
  python "$AGENTS/repairer.py" \
    --prompts_file "$PROMPTS" \
    --code_dir     "$DEV_OUT" \
    --review_dir   "$REV_OUT" \
    --output_dir   "$REP_OUT" \
    --model        "$MODEL" \
    --temperature  0.0 \
    --num_samples  "$SAMPLES" \
    --start        "$START" \
    --end          "$END"
  run_solar "repairer" "$REP_OUT"

  log_stage "3b  Repairer v1 (comparison)" "$REV_OUT/*_v1" "$REP_V1_OUT"
  TMP_V1="$BASE/reviewer_v1_links"
  mkdir -p "$TMP_V1"
  for f in "$REV_OUT"/task_*_review_v1.jsonl; do
    [[ -f "$f" ]] || continue
    tid=$(basename "$f" _review_v1.jsonl | sed 's/task_//')
    ln -sf "$(realpath "$f")" "$TMP_V1/task_${tid}_review.jsonl"
  done
  python "$AGENTS/repairer.py" \
    --prompts_file "$PROMPTS" \
    --code_dir     "$DEV_OUT" \
    --review_dir   "$TMP_V1" \
    --output_dir   "$REP_V1_OUT" \
    --model        "$MODEL" \
    --temperature  0.0 \
    --num_samples  "$SAMPLES" \
    --start        "$START" \
    --end          "$END"
  run_solar "repairer_v1" "$REP_V1_OUT"

  echo ""
  echo "$SEP"
  echo "  CBS_before:   $DEV_OUT"
  echo "  CBS_after_v2: $REP_OUT"
  echo "  CBS_after_v1: $REP_V1_OUT"
  echo "$SEP"
fi

# =============================================================================
# Experiment 3
# =============================================================================
if [[ "$EXP" == "3" ]]; then
  [[ -z "$STYLE" ]] && STYLE="agent"
  require_solar
  BASE="$REPO/results/exp3_fma"
  FAIR_SPEC_OUT="$BASE/fair_spec"
  DEV_OUT="$BASE/developer"
  FMA_REV_OUT="$BASE/fma_reviewer"
  FMA_REP_OUT="$BASE/repairer"
  mkdir -p "$FAIR_SPEC_OUT" "$DEV_OUT" "$FMA_REV_OUT" "$FMA_REP_OUT"

  echo "$SEP"
  echo "  EXP 3 – FMA pipeline"
  echo "  model=$MODEL  tasks=$START-$END  samples=$SAMPLES  rounds=$ROUNDS"
  echo "$SEP"

  log_stage "A  Fairness Requirement Analyst" "$PROMPTS" "$FAIR_SPEC_OUT"
  python "$FMA/bias_aware_requirements.py" \
    --prompts_file "$PROMPTS" \
    --output_dir   "$FAIR_SPEC_OUT" \
    --model        "$MODEL" \
    --num_samples  1 \
    --start        "$START" \
    --end          "$END"

  log_stage "1  Developer" "$PROMPTS + $FAIR_SPEC_OUT" "$DEV_OUT"
  python "$AGENTS/developer.py" "${COMMON[@]}" \
    --prompt_style "$STYLE" \
    --output_dir   "$DEV_OUT" \
    --spec_dir     "$FAIR_SPEC_OUT"

  run_solar "developer" "$DEV_OUT"

  # ── Iterative review + repair loop (--rounds controls iterations) ──────────
  # Round 1 reads from developer output.
  # Each subsequent round reads from the previous round's repairer output.
  # Results are named: repairer_round1/, repairer_round2/, ..., repairer/ (final)
  CURRENT_CODE_DIR="$DEV_OUT"
  for round in $(seq 1 "$ROUNDS"); do
    if [[ "$round" -lt "$ROUNDS" ]]; then
      ROUND_REP_OUT="$BASE/repairer_round${round}"
    else
      ROUND_REP_OUT="$FMA_REP_OUT"   # final round goes to canonical repairer/
    fi
    mkdir -p "$ROUND_REP_OUT"

    log_stage "2  FMA Reviewer (round $round/$ROUNDS)" "$CURRENT_CODE_DIR" "$FMA_REV_OUT"
    python "$FMA/bias_aware_reviewer.py" \
      --prompts_file "$PROMPTS" \
      --code_dir     "$CURRENT_CODE_DIR" \
      --output_dir   "$FMA_REV_OUT" \
      --model        "$MODEL" \
      --num_samples  "$SAMPLES" \
      --start        "$START" \
      --end          "$END"

    log_stage "3  FMA Repairer (round $round/$ROUNDS)" "$CURRENT_CODE_DIR + $FMA_REV_OUT" "$ROUND_REP_OUT"
    python "$FMA/bias_repairer.py" \
      --prompts_file "$PROMPTS" \
      --code_dir     "$CURRENT_CODE_DIR" \
      --review_dir   "$FMA_REV_OUT" \
      --output_dir   "$ROUND_REP_OUT" \
      --model        "$MODEL" \
      --num_samples  "$SAMPLES" \
      --num_rounds   1 \
      --start        "$START" \
      --end          "$END"

    CURRENT_CODE_DIR="$ROUND_REP_OUT"
  done

  run_solar "repairer" "$FMA_REP_OUT"

  echo ""
  echo "$SEP"
  echo "  CBS_before:    $MODEL_DIR/test_result/developer/"
  echo "  CBS_after_fma: $MODEL_DIR/test_result/repairer/"
  echo "$SEP"
fi