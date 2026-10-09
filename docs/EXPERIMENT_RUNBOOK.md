# EMSE Revision Experiment Runbook

This is the execution checklist for the revised GPT-6 Luna arm.

## Fixed configuration

Use the same model/reasoning configuration throughout the four RQs:

```text
OPENAI_MODEL=gpt-6-luna
OPENAI_REASONING_EFFORT=none
OPENAI_REASONING_MODE=standard
REVISION_COMMON_TEMPERATURE=0.8
FLOWGEN_TEMPERATURE=0.8
```

RQ1 is the only temperature-sensitivity experiment and sweeps 0.2, 0.4, 0.6, 0.8, 1.0. Temperature 0.8 is its matched anchor with RQ2-RQ4.

## 0. Setup

```bash
cd social_bias_revision
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_revision.txt
cp .env.example .env
# Edit .env locally and set OPENAI_API_KEY only.
python scripts/preflight.py
```

Do not put the API key in source files or chat.

## 1. Smoke campaign

Run one task through every revised condition:

```bash
bash scripts/smoke_all.sh smoke1
```

Verify completeness:

```bash
python scripts/check_campaign.py --tag smoke1 --smoke
```

Inspect at least:

```text
results/rq1/smoke1_rq1/temp_0.8/developer/task_0_generated_code.jsonl
results/rq2/smoke1_rq2/rq2_cot_only/developer/task_0_generated_code.jsonl
results/rq3_flowgen/smoke1_rq3_rep1__waterfall/run_config.json
results/rq3_flowgen/smoke1_rq3_rep1__waterfall/final_code/task_0_generated_code.jsonl
results/rq3_flowgen/smoke1_rq3_rep1__no_requirement_tester/final_code/task_0_generated_code.jsonl
results/rq4/smoke1_rq4_rep1/fairness_requirements/task_0_requirements.jsonl
results/rq4/smoke1_rq4_rep1/round1/fairness_reviewer/task_0_review.jsonl
results/rq4/smoke1_rq4_rep1/round1/fairness_repairer/task_0_generated_code.jsonl
```

Check cost/tokens:

```bash
python scripts/summarize_usage.py
```

## 2. Recommended intermediate pilot

Before the expensive RQ3 campaign, run tasks 0-9 (ten tasks) for all RQs/components. Use separate IDs so this pilot is not mixed with the full repetitions.

```bash
bash scripts/run_pilot10.sh pilot10
```

This includes Solar evaluation for RQ1/RQ2/RQ3/RQ4 and prints token/cost usage when finished.

## 3. Full campaign, safest approach

Run each RQ separately so failures/costs are easy to isolate.

```bash
bash scripts/run_rq1_full.sh luna_revision_rq1
bash scripts/run_rq2_full.sh luna_revision_rq2
bash scripts/run_rq3_full.sh luna_revision_rq3
bash scripts/run_rq4_full.sh luna_revision_rq4
```

The full workloads are:

- RQ1: 343 tasks x 5 temperatures x 5 generations = 8,575 code generations.
- RQ2: 343 tasks x 6 prompt conditions x 5 generations = 10,290 code generations.
- RQ3: 343 tasks x 12 unique configurations x 3 independent repetitions. Each FlowGen task contains multiple LLM calls.
- RQ4: 343 tasks x 3 independent repetitions, with up to 3 FMA repair rounds per task.

Full RQ3/RQ4 use distinct run IDs for the three stochastic repetitions.

Alternatively, run everything sequentially:

```bash
bash scripts/run_all_full.sh luna_revision
```

The per-RQ approach is recommended.

## 4. Resume after a crash or quota/rate interruption

Re-run the exact same command with the same run ID. Per-task output files that already exist are skipped. A new stochastic repetition must use a new replicate/run ID.

Examples:

```bash
python commands/run_rq3_revision.py --replicate-id luna_revision_rq3_rep2 --start 0 --end 343 --evaluate
python commands/run_rq4_revision.py --run-id luna_revision_rq4_rep2 --start 0 --end 343 --rounds 3 --evaluate
```

Do not use `--overwrite` unless intentionally replacing outputs.

## 5. Completeness check

If the four scripts above used exactly these IDs:

```bash
python scripts/check_campaign.py --tag luna_revision --full
```

The four per-RQ commands shown above use the same naming convention as the checker. You can therefore run them separately and still verify the complete campaign with the same `--tag luna_revision` command.

## 6. Token/cost accounting

```bash
python scripts/summarize_usage.py
```

All calls append to `results/api_usage.jsonl`. Keep this file with the replication package.

## 7. RQ3 confidence intervals

Example: Waterfall across the three full replicates:

```bash
python analysis/bootstrap_cbs.py \
  --roots results/rq3_flowgen/luna_revision_rq3_rep1__waterfall/solar \
          results/rq3_flowgen/luna_revision_rq3_rep2__waterfall/solar \
          results/rq3_flowgen/luna_revision_rq3_rep3__waterfall/solar \
  --agent final
```

Repeat the same command by changing `waterfall` to any of the other 11 RQ3 configurations.

## 8. RQ4 confidence interval and paired FMA reduction

```bash
python analysis/bootstrap_cbs.py \
  --roots results/rq4/luna_revision_rq4_rep1/solar \
          results/rq4/luna_revision_rq4_rep2/solar \
          results/rq4/luna_revision_rq4_rep3/solar \
  --agent round3 --before-agent developer
```

This cluster-bootstraps task IDs and keeps all three repetitions of a sampled task together.

## 9. RQ3 reconstruction note

The 2025 hand-off did not contain the source for the four role-ablation workflows. The revision package reconstructs them from the manuscript definition:

- no Tester;
- no Architect + Tester;
- no Requirement Engineer + Tester;
- Developer only.

Details are in `docs/RQ3_ABLATION_IMPLEMENTATION.md`. Report these honestly as reconstructed revision configurations, not recovered historical code.

## 10. Functional-correctness comment

The existing benchmark does not define a unique ground-truth Boolean decision rule for many tasks. Therefore the repository deliberately does not invent a full logical-correctness oracle. See `docs/FUNCTIONAL_CORRECTNESS_PLAN.md`. Pass@attribute should be described as attribute-level task alignment unless/until a separately adjudicated executable-oracle subset is added.

## FlowGen compatibility note for current models

The original 2025 FlowGen implementation assumed GPT-3.5-style behavior. Two
compatibility fixes are enabled for the revision runs:

1. `FLOWGEN_BENCHMARK_MODE=1` adds the same neutral benchmark-execution
   constraint to every RQ3 configuration. It tells the model that the supplied
   SocialBias-Bench task is self-contained, to preserve the Boolean interface,
   and to produce a concrete best-effort implementation instead of requesting
   external policies or returning `NotImplementedError`. It contains no
   fairness instruction.
2. FlowGen outputs are normalized by extracting the final benchmark method from
   Markdown/prose before Solar evaluation. This changes formatting only, not
   generated logic.

As in the handed-over FlowGen `main.py`, failure of a downstream review/repair
step does not discard an earlier code artifact. The latest available code is
still evaluated, while the step error is stored in the output metadata.

Solar now records malformed or runtime-failing code as `failed`, rather than
silently treating it as an absent unbiased sample. CBS remains computed over
executable samples, and `Executable_rate` reports the denominator explicitly.
