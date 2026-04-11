bash commands/run_pipeline.sh --exp 3 \
    --start 0 --end 5 --samples 1 --rounds 2 \
    --solar_dir ~/solar_comprehensive/fairness_test \
    --model_dir ~/solar_comprehensive/results/gpt35


## score
python score/calculate_scores.py \
    --model_dir ~/solar_comprehensive/results/gpt35 \
    --agent developer --start 0 --end 10 --samples 1

python score/calculate_scores.py \
    --model_dir ~/solar_comprehensive/results/gpt35 \
    --agent repairer --start 0 --end 10 --samples 1