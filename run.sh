# bash commands/run_pipeline.sh --exp 3 \
#     --start 0 --end 2 \
#     --solar_dir ~/solar_comprehensive/fairness_test \
#     --model_dir ~/solar_comprehensive/results/gpt35

# # Full Exp 3 with upstream specs
# bash commands/run_pipeline.sh --exp 3 \
#     --with_spec \
#     --solar_script ~/solar/fairness_test/commands/agent_commands_bash.sh \
#     --model_dir ~/solar/results/gpt35

# bash commands/run_pipeline.sh --exp 3     --start 0 --end 2     --solar_dir ~/solar_comprehensive/fairness_test     --model_dir ~/solar_comprehensive/results/gpt35

bash commands/run_pipeline.sh --exp 3 \
    --start 0 --end 2 \
    --samples 1 \
    --solar_dir ~/solar_comprehensive/fairness_test \
    --model_dir ~/solar_comprehensive/results/gpt35



# for the score
# Full run, 5 samples
python score/calculate_scores.py \
    --model_dir ~/solar_comprehensive/results/gpt35 \
    --agent developer \
    --start 0 --end 343 --samples 5

# Smoke test, 2 tasks, 1 sample
python score/calculate_scores.py \
    --model_dir ~/solar_comprehensive/results/gpt35 \
    --agent developer \
    --start 0 --end 2 --samples 1

# After FMA repair
python score/calculate_scores.py \
    --model_dir ~/solar_comprehensive/results/gpt35 \
    --agent repairer \
    --start 0 --end 343 --samples 5