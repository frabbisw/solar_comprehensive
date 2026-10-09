bash commands/run_pipeline.sh --exp 3 \
    --start 0 --end 343 --samples 5 --rounds 1 \
    --solar_dir ~/solar_comprehensive/fairness_test \
    --model_dir ~/solar_comprehensive/results/gpt35

# CBS_before
python score/calculate_scores.py \
    --model_dir ~/solar_comprehensive/results/gpt35 \
    --agent developer --start 0 --end 343 --samples 5

# CBS after round 1
python score/calculate_scores.py \
    --model_dir ~/solar_comprehensive/results/gpt35 \
    --agent repairer_round1 --start 0 --end 343 --samples 5

python score/calculate_scores.py \
    --model_dir ~/solar_comprehensive/results/gpt35 \
    --agent repairer_round1 --start 0 --end 343 --samples 5 \
    --related_version v2



bash commands/run_pipeline.sh --exp 3     --start 0 --end 3 --samples 1 --rounds 3     --solar_dir ~/solar_comprehensive/fairness_test     --model_dir ~/solar_comprehensive/results/gpt35

# only requirements
# Step A: Functional Requirement Analyst
python agents/requirements.py \
    --prompts_file dataset/prompts.jsonl \
    --output_dir   results/exp3_fma/func_spec \
    --model        gpt \
    --num_samples  1 \
    --start        0 \
    --end          5

# Step B: Fairness Requirement Analyst (round 1)
python fma/bias_aware_requirements.py \
    --prompts_file dataset/prompts.jsonl \
    --output_dir   results/exp3_fma/fair_spec_round1 \
    --prd_dir      results/exp3_fma/func_spec \
    --model        gpt \
    --num_samples  1 \
    --start        0 \
    --end          5

# 1 requirements refinement round, 2 reviewer/repairer rounds
bash commands/run_pipeline.sh --exp 3 \
    --start 0 --end 343 --samples 5 \
    --rounds 2 --fma_req_rounds 1 \
    --solar_dir ~/solar_comprehensive/fairness_test \
    --model_dir ~/solar_comprehensive/results/gpt35

# 2 requirements refinement rounds
bash commands/run_pipeline.sh --exp 3 \
    --start 0 --end 343 --samples 5 \
    --rounds 1 --fma_req_rounds 2 \
    --solar_dir ~/solar_comprehensive/fairness_test \
    --model_dir ~/solar_comprehensive/results/gpt35

python score/calculate_scores.py     --model_dir ~/solar_comprehensive/results/gpt35     --agent repairer --start 0 --end 30 --samples 1