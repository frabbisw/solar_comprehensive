bash commands/run_pipeline.sh --exp 3 \
    --start 0 --end 2 \
    --solar_dir ~/solar_comprehensive/fairness_test \
    --model_dir ~/solar_comprehensive/results/gpt35

# Full Exp 3 with upstream specs
bash commands/run_pipeline.sh --exp 3 \
    --with_spec \
    --solar_script ~/solar/fairness_test/commands/agent_commands_bash.sh \
    --model_dir ~/solar/results/gpt35

bash commands/run_pipeline.sh --exp 3     --start 0 --end 2     --solar_dir ~/solar_comprehensive/fairness_test     --model_dir ~/solar_comprehensive/results/gpt35