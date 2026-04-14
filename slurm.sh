#!/bin/bash

#SBATCH -J solar_job
#SBATCH -n 4
#SBATCH --mem=60G
#SBATCH --time=72:00:00
#SBATCH -o _%x%j.out
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=osdefr@gmail.com

# Parse named arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --exp) exp="$2"; shift ;;
        --start) start="$2"; shift ;;
        --end) end="$2"; shift ;;
        --samples) samples="$2"; shift ;;
        --rounds) rounds="$2"; shift ;;
        --solar_dir) solar_dir="$2"; shift ;;
        --model_dir) model_dir="$2"; shift ;;
        --temp) temp="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "Experiment: $exp"
echo "Start: $start"
echo "End: $end"
echo "Samples: $samples"
echo "Rounds: $rounds"
echo "Solar Directory: $solar_dir"
echo "Model Directory: $model_dir"
echo "Temperature: $temp"   

source /etc/profile.d/modules.sh
module load python/3.11.6
module load anaconda/3.2024.10.1

eval "$(conda shell.bash hook)"
conda activate solar

bash commands/run_pipeline.sh \
  --exp "$exp" \
  --start "$start" \
  --end "$end" \
  --samples "$samples" \
  --rounds "$rounds" \
  --solar_dir "$solar_dir" \
  --model_dir "$model_dir" \
  --temp "$temp"

python score/calculate_scores.py \
  --model_dir "$model_dir" \
  --agent developer \
  --start "$start" \
  --end "$end" \
  --samples "$samples"

python score/calculate_scores.py \
  --model_dir "$model_dir" \
  --agent repairer_round1 \
  --start "$start" \
  --end "$end" \
  --samples "$samples"

python score/calculate_scores.py \
  --model_dir "$model_dir" \
  --agent repairer_round2 \
  --start "$start" \
  --end "$end" \
  --samples "$samples"

python score/calculate_scores.py \
  --model_dir "$model_dir" \
  --agent repairer_round3 \
  --start "$start" \
  --end "$end" \
  --samples "$samples"


#python score/calculate_scores.py     --model_dir ~/solar/solar_comprehensive/results/gpt35     --agent repairer_round1 --start 0 --end 100 --samples 1
#python score/calculate_scores.py     --model_dir ~/solar/solar_comprehensive/results/gpt35     --agent repairer_round1 --start 0 --end 100 --samples 1 --related_version v2
#python score/calculate_scores.py     --model_dir ~/solar/solar_comprehensive/results/gpt35     --agent repairer_round2 --start 0 --end 100 --samples 1
#python score/calculate_scores.py     --model_dir ~/solar/solar_comprehensive/results/gpt35     --agent repairer_round3 --start 0 --end 100 --samples 1


# sbatch slurm.sh --exp 3     --start 0 --end 100 --samples 1 --rounds 3     --solar_dir ~/solar_comprehensive/fairness_test     --model_dir ~/solar_comprehensive/results/gp>
