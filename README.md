# Social Bias EMSE Major-Revision Experiments

This repository combines the original Solar/FMA codebase with the FlowGen hand-off used for RQ3 and adds clean revision runners for the EMSE major revision of **Social Bias in LLM-Generated Code: Benchmark and Mitigation**.

The revision package keeps historical code traceable, but **all new results go under `results/` with new run IDs**. Old FlowGen virtual environments, generated workspaces, caches, and plaintext API credentials were removed.


## Recommended staged execution

For the current revision campaign, use the **single-run-first** sequence in
`docs/STAGED_RUN_PLAN.md`: full RQ1 across all five temperatures first, one
complete RQ4 run, a small RQ3 pilot, one complete RQ3 run, and then all RQ2
prompt styles. Additional independent RQ3/RQ4 runs come afterward.

## 1. Revision configuration

To keep the new GPT arm comparable across the four RQs, use the same model/reasoning configuration everywhere:

```text
OPENAI_MODEL=gpt-6-luna
OPENAI_REASONING_EFFORT=none
OPENAI_REASONING_MODE=standard
REVISION_COMMON_TEMPERATURE=0.8
FLOWGEN_TEMPERATURE=0.8
```

RQ1 intentionally varies temperature and includes **0.8 as the common anchor**. RQ2, RQ3, and RQ4 use 0.8. Because RQ1 is a temperature-sensitivity experiment, reasoning must remain `none` for the common RQ1-RQ4 configuration.

The OpenAI key is read only from `.env`; do not put it in source code or commit it.

**Security:** the original FlowGen hand-off contained plaintext API keys. They are not present here. Rotate/revoke those historical keys if that has not already been done.

## 2. What is implemented

### RQ1

GPT-6 Luna replacement arm over all 343 tasks, five generations per task, temperatures:

`0.2, 0.4, 0.6, 0.8, 1.0`

### RQ2

Six disentangled prompt conditions over all 343 tasks, five generations per task:

- `rq2_default` (identical to the original RQ1 Default prompt)
- `rq2_cot_only`
- `rq2_fairness_only`
- `rq2_positive_role_only`
- `rq2_cot_fairness`
- `rq2_positive_cot_fairness`

This separates CoT, fairness wording, and positive-role prompting instead of confounding them.

### RQ3

The runner contains all **12 unique configurations** used by the three RQ3 analyses:

Workflow structure:

- `raw`
- `waterfall`
- `scrum`

Fairness-aware role prompting:

- `waterfall` (same clean baseline, reused analytically)
- `waterfall_pm_fair`
- `waterfall_architect_fair`
- `waterfall_developer_fair`
- `waterfall_qa_fair`
- `waterfall_all_fair`

Role ablation:

- `waterfall` (same clean baseline, reused analytically)
- `no_tester`
- `no_architect_tester`
- `no_requirement_tester`
- `developer_only`

The four ablation source variants were missing from the 2025 hand-off. They are now reconstructed directly from the manuscript's role-removal definition. The exact operationalization is documented in `docs/RQ3_ABLATION_IMPLEMENTATION.md`. They must be described as **reconstructed revision configurations**, not recovered historical code.

### RQ4

The revision runner implements the manuscript-level FMA pipeline:

```text
Functional Requirements Analyst
  -> Fairness Requirements Analyst
  -> Developer
  -> Functional Reviewer
  -> Functional Repairer
  -> Fairness Reviewer
  -> Fairness Repairer
  -> repeat up to 3 rounds
```

The Fairness Requirements Analyst prepares fairness-aware requirements. The Fairness Reviewer independently assesses the original task and generated method without treating upstream attribute classifications as authoritative. All three rounds perform fresh functional and fairness reviews, even when an earlier review passes. Repairers are invoked only when issues are reported. Solar is used only for external evaluation and is never visible to FMA agents.

## 3. Setup

Preferred environment: **Conda with Python 3.11**. The commands below assume
the zip was downloaded to the Windows `Downloads` folder and is being run from
WSL.

```bash
WINUSER=$(cmd.exe /c echo %USERNAME% | tr -d '\r')
ZIP="/mnt/c/Users/$WINUSER/Downloads/social_bias_revision_clean_v4.zip"

cd ~
unzip -o "$ZIP"
cd ~/social_bias_revision

conda create -n socialbias python=3.11 -y   # only the first time
conda activate socialbias
pip install -r requirements_revision.txt

cp -n .env.example .env
nano .env
```

Set your key locally in `.env`:

```text
OPENAI_API_KEY=YOUR_KEY_HERE
```

If `socialbias` already exists, do not recreate it; just activate it. Using
`unzip -o` updates repository files but does not delete an existing `.env` or
existing result directories. Do **not** paste your API key into chat.

## 4. Preflight

Always run this first:

```bash
python scripts/preflight.py
```

It checks the 343-task dataset, the 12 RQ3 configurations, required files, the common temperature, and that no hidden 0.0-temperature override remains in the active RQ4 agents.

## 5. One-task smoke tests

### Recommended: exercise everything

This runs one task through RQ1, all six RQ2 conditions, all twelve RQ3 configurations, and one RQ4 repair round, then prints token/cost usage:

```bash
bash scripts/smoke_all.sh smoke1
```

If it stops, fix that issue and run the same command again. Existing successful task files are skipped.

### Individual smoke commands

RQ1 common anchor:

```bash
python commands/run_rq1_revision.py \
  --run-id smoke_rq1 --start 0 --end 1 --samples 1 --temps 0.8

bash commands/evaluate_solar.sh \
  --response-dir results/rq1/smoke_rq1/temp_0.8/developer \
  --out-dir results/rq1/smoke_rq1/solar_temp_0.8 \
  --label developer --start 0 --end 1 --samples 1
```

RQ2 all six conditions:

```bash
python commands/run_rq2_revision.py \
  --run-id smoke_rq2 --start 0 --end 1 --samples 1
```

One RQ3 configuration:

```bash
python flowgen/run_flowgen.py \
  --configuration waterfall --start 0 --end 1 --run-id smoke_waterfall
```

One reconstructed RQ3 ablation:

```bash
python flowgen/run_flowgen.py \
  --configuration no_requirement_tester \
  --start 0 --end 1 --run-id smoke_no_req_tester
```

All twelve RQ3 configurations for one task:

```bash
python commands/run_rq3_revision.py \
  --replicate-id smoke_rq3_rep1 --start 0 --end 1 --evaluate
```

RQ4 one task, one round:

```bash
python commands/run_rq4_revision.py \
  --run-id smoke_rq4_rep1 --start 0 --end 1 --rounds 1 --evaluate
```

## 6. Full rebuttal experiments

Run these **only after `smoke_all.sh` completes successfully and you inspect a few generated artifacts**.

### RQ1 full GPT-6 Luna arm

```bash
bash scripts/run_rq1_full.sh luna_revision_rq1
```

This runs 343 tasks × 5 temperatures × 5 generations and then Solar evaluation for each temperature.

### RQ2 full prompt study

```bash
bash scripts/run_rq2_full.sh luna_revision_rq2 luna_revision_rq1
```

This evaluates all six RQ2 conditions. Default is reused from the identical
RQ1 t=0.8 Luna outputs; the other five conditions generate 343 × 5 × 5 =
8,575 new completions.

### RQ3 one complete execution

```bash
bash scripts/run_rq3_full.sh luna_rq3_run1
```

This runs all 12 configurations on all 343 tasks once and evaluates every configuration with Solar. Use `scripts/run_rq3_three_reps.sh` only later when you deliberately want three independent executions.

If you prefer to run one replicate at a time:

```bash
python commands/run_rq3_revision.py \
  --replicate-id luna_revision_rq3_rep1 --start 0 --end 343 --evaluate

python commands/run_rq3_revision.py \
  --replicate-id luna_revision_rq3_rep2 --start 0 --end 343 --evaluate

python commands/run_rq3_revision.py \
  --replicate-id luna_revision_rq3_rep3 --start 0 --end 343 --evaluate
```

### RQ4 one complete FMA execution

```bash
bash scripts/run_rq4_full.sh luna_rq4_run1
```

Equivalent explicit command:

```bash
python commands/run_rq4_revision.py \
  --run-id luna_rq4_run1 --start 0 --end 343 --rounds 3 --evaluate
```

Later, add independent runs with new IDs:

```bash
bash scripts/run_rq4_once.sh luna_rq4_run2
bash scripts/run_rq4_once.sh luna_rq4_run3
```

### Everything sequentially

`scripts/run_all_full.sh` is kept for convenience, but the staged plan in
`docs/STAGED_RUN_PLAN.md` is safer and is the recommended workflow for the
revision.

## 7. Resume behavior

Use the **same run ID** after an interruption. Successful per-task outputs are skipped. Do not use `--overwrite` unless you intentionally want to replace a run.

Use different IDs for independent stochastic repetitions, for example:

```text
luna_revision_rq3_rep1
luna_revision_rq3_rep2
luna_revision_rq3_rep3
```

## 8. API usage and cost

All new OpenAI calls append usage to:

```text
results/api_usage.jsonl
```

View totals at any time:

```bash
python scripts/summarize_usage.py
```

Reasoning tokens are shown separately but are not double-counted in estimated output cost.

## 9. Historical FlowGen hand-off

Read:

- `docs/FLOWGEN_HANDOFF_AUDIT.md`
- `docs/RQ3_ABLATION_IMPLEMENTATION.md`

Important historical facts:

- raw GPT and Waterfall had 343-task artifacts;
- Scrum and fairness-role experiments in the hand-off only covered a common 70-task subset;
- the historical 343-task Waterfall logs already contained a fairness sentence in the QA prompt, so they are not a clean no-fairness baseline;
- the role-ablation source was missing and has therefore been explicitly reconstructed for the revision.

For the new revision campaign, do not mix those historical FlowGen outputs with the new runs.

## 10. Functional-correctness reviewer comment

The benchmark currently specifies which attributes are related/sensitive, but many task docstrings do **not** provide a unique executable ground-truth decision rule (for example, they do not state an exact financial-aid threshold). Therefore a true logical-correctness oracle cannot be generated automatically from the existing benchmark without inventing new task semantics.

Do not present Pass@attribute as full functional correctness. The stronger functional-validation experiment should be handled separately using manually defined/adjudicated executable oracles for a documented task subset, or the claim should be narrowed to attribute-level task alignment. This is intentionally not silently fabricated by the runner.

## 11. Post-run completeness and confidence intervals

A concise execution checklist is in `docs/EXPERIMENT_RUNBOOK.md`.

For a campaign launched with `bash scripts/run_all_full.sh luna_revision`, verify that every expected task/replicate was produced:

```bash
python scripts/check_campaign.py --tag luna_revision --full
```

For the one-task smoke suite:

```bash
python scripts/check_campaign.py --tag smoke1 --smoke
```

Example RQ3 95% task-cluster bootstrap CI for Waterfall:

```bash
python analysis/bootstrap_cbs.py \
  --roots results/rq3_flowgen/luna_revision_rq3_rep1__waterfall/solar \
          results/rq3_flowgen/luna_revision_rq3_rep2__waterfall/solar \
          results/rq3_flowgen/luna_revision_rq3_rep3__waterfall/solar \
  --agent final
```

Example paired RQ4 Developer-to-Round-3 FMA reduction:

```bash
python analysis/bootstrap_cbs.py \
  --roots results/rq4/luna_revision_rq4_rep1/solar \
          results/rq4/luna_revision_rq4_rep2/solar \
          results/rq4/luna_revision_rq4_rep3/solar \
  --agent round3 --before-agent developer
```

### Important RQ3 revision compatibility behavior

For current OpenAI models, `FLOWGEN_BENCHMARK_MODE=1` is enabled by default.
This is a neutral, identical constraint for all RQ3 configurations: treat each
SocialBias-Bench prompt as a self-contained small coding task, preserve the
provided Boolean method interface, and produce a concrete best-effort method
instead of requesting an external policy or refusing an underspecified task.
It does not mention fairness. Set `FLOWGEN_BENCHMARK_MODE=0` only to reproduce
the unadapted 2025 FlowGen prompting behavior.

FlowGen responses are also normalized to the final method definition before
Solar evaluation, because current models may surround code with Markdown or
explanatory prose. Non-executable generations are explicitly marked failed and
reported through the executable-rate metric.
