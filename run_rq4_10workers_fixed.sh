#!/usr/bin/env bash
set -u

cd "$HOME/PycharmProjects/social_bias_revision" || exit 1

STARTS=(0 35 70 105 140 174 208 242 276 310)
ENDS=(35 70 105 140 174 208 242 276 310 343)

mkdir -p rq4_worker_logs_fixed

for idx in "${!STARTS[@]}"; do
    i=$((idx + 1))
    start="${STARTS[$idx]}"
    end="${ENDS[$idx]}"

    echo "Starting worker $i: tasks $start-$((end-1))"

    (
        export OPENAI_REASONING_EFFORT=none
        export OPENAI_REASONING_MODE=standard

        # Shared throttle across ALL 10 processes
        export OPENAI_MIN_REQUEST_INTERVAL_SECONDS=2

        # More resilience for a long multi-worker run
        export OPENAI_MAX_RETRIES=8
        export OPENAI_MAX_PROMPT_RETRIES=10

        # Keep usage/event logs separate so simultaneous processes never
        # write to the same JSONL file.
        export OPENAI_USAGE_LOG="results/api_usage_rq4_run1_w${i}.jsonl"
        export OPENAI_PROVIDER_EVENT_LOG="results/provider_events_rq4_run1_w${i}.jsonl"

        python commands/run_rq4_revision.py \
            --run-id "luna_rq4_run1_fixed_w${i}" \
            --start "$start" \
            --end "$end" \
            --rounds 3 \
            --temperature 0.8 \
            > "rq4_worker_logs_fixed/w${i}.log" 2>&1
    ) &

    echo $! > "rq4_worker_logs_fixed/w${i}.pid"

    # Small initial staggering; global throttle handles subsequent calls.
    sleep 1
done

echo
echo "All 10 RQ4 workers launched."
echo "Logs: rq4_worker_logs_fixed/"
