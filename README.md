# Social Bias in LLM-Generated Code: Benchmark and Mitigation

**Reproduction repository for the Empirical Software Engineering (EMSE) major revision**

This repository contains the **SocialBias-Bench** coding tasks, the **Solar** fairness evaluation framework, and the generation/mitigation implementations used for four research questions (RQs). It combines the original implementation with the revised experiment runners and the FlowGen-based RQ3 workflows.

> **Reproduction scope.** The commands below reproduce the **revised GPT-6 Luna experimental arm**, not every historical model from the original paper. Generation requires access to the configured model through the API. The repository excludes generated results, local configuration, API keys, and large logs. These should be archived separately.

## Research questions and coverage

All revised studies use **343 tasks**, indexed **0–342**, from `dataset/prompts.jsonl`.

| Research question | Study | Revised experimental conditions | Samples |
| --- | --- | --- | --- |
| **RQ1** | Effect of generation temperature on social bias | `0.2`, `0.4`, `0.6`, `0.8`, `1.0` | 5 generated methods per task per temperature |
| **RQ2** | Effect of prompt-level mitigation | Default, CoT only, fairness only, positive role only, CoT + fairness, positive role + CoT + fairness | 5 generated methods per task per condition, at temperature `0.8` |
| **RQ3** | Effect of multi-agent development workflow, fairness-aware roles, and role ablations | 12 distinct FlowGen configurations | 1 output per task per configuration per independent run |
| **RQ4** | Fairness Monitor Agent (FMA) | Developer baseline and three functional/fairness review-and-repair rounds | 1 output per task per stage per independent run |

**Fairness evaluation:** Solar evaluates the generated Python methods using the benchmark's task-specific tests. We report Code Bias Score (CBS), Pass@attribute, and executable rate. Lower CBS indicates fewer detected benchmark-defined fairness violations. Pass@attribute measures task-related attribute usage; **neither Pass@attribute nor executable rate is a complete oracle for semantic functional correctness**. See [Functional correctness](#functional-correctness-and-evaluation-limits).

## Repository layout

```text
agents/                       RQ1/RQ2 single-model code generation
agents_full/                  RQ4 functional requirements, developer, reviewer, repairer
fma/                          Historical FMA implementation (retained for traceability)
fma_full/                     RQ4 fairness requirements, reviewer, repairer
flowgen/                      RQ3 FlowGen and workflow configurations
fairness_test/                Solar implementation and test suites
score/                        CBS and Pass@attribute calculations
commands/                     RQ1–RQ4 Python runners and Solar runner
scripts/                      Smoke tests, full-run wrappers, completeness/usage checks
analysis/                     Bootstrap analysis
 dataset/prompts.jsonl        343 SocialBias-Bench tasks
 docs/                        Experimental design and implementation notes
results/                      Generated outputs (local; not tracked by Git)
```

RQ3 includes reconstructed ablation configurations. They are **new revision implementations based on the described role removals**, not recovered historical source code; see `docs/RQ3_ABLATION_IMPLEMENTATION.md`.

## 1. Environment and setup

Tested workflow: Linux/Ubuntu, **Python 3.11**, Conda environment named `socialbias`. From the checked-out repository root:

```bash
conda create -n socialbias python=3.11 -y   # first time only
conda activate socialbias
pip install -r requirements_revision.txt

cp -n .env.example .env
nano .env
```

Configure `.env` locally (never commit it):

```dotenv
OPENAI_API_KEY=YOUR_API_KEY
OPENAI_MODEL=gpt-6-luna
OPENAI_REASONING_EFFORT=none
OPENAI_REASONING_MODE=standard
REVISION_COMMON_TEMPERATURE=0.8
FLOWGEN_TEMPERATURE=0.8
FLOWGEN_BENCHMARK_MODE=1
SOLAR_KEEP_RAW=0
```

The same model/reasoning configuration is used across the revised studies. RQ1 varies temperature; temperature `0.8` provides the matched anchor for RQ2–RQ4. `FLOWGEN_BENCHMARK_MODE=1` applies the **same task-format compatibility instruction** to every RQ3 configuration and does not introduce an extra fairness rule.

Verify the installation and benchmark inputs:

```bash
python scripts/preflight.py
```

Before paying for a full run, execute the small smoke test:

```bash
bash scripts/smoke_all.sh smoke1
python scripts/check_campaign.py --tag smoke1 --smoke
```

Use different run IDs for a new experiment. A repeated ID can reuse existing per-task outputs instead of making independent new model calls.

## 2. Reproduce RQ1: temperature study

```bash
bash scripts/run_rq1_full.sh reproduce_rq1_rep1
```

This generates `343 × 5 temperatures × 5 samples = 8,575` methods, then evaluates each temperature with Solar. Generated code is under:

```text
results/rq1/reproduce_rq1_rep1/temp_0.8/developer/
```

The same structure exists for temperatures `0.2`, `0.4`, `0.6`, and `1.0`. Solar scores for temperature `0.8` are at:

```text
results/rq1/reproduce_rq1_rep1/solar_temp_0.8/test_result/developer/scores_v1.json
```

## 3. Reproduce RQ2: prompt interventions

**Run RQ1 first.** The RQ2 Default condition uses the same prompt and reuses the five existing RQ1 methods per task at temperature `0.8` rather than generating identical completions again:

```bash
bash scripts/run_rq2_full.sh reproduce_rq2_rep1 reproduce_rq1_rep1
```

The six conditions are:

```text
rq2_default
rq2_cot_only
rq2_fairness_only
rq2_positive_role_only
rq2_cot_fairness
rq2_positive_cot_fairness
```

The command generates **8,575 new methods** for the five non-Default conditions; all six conditions are evaluated with Solar. Output example:

```text
results/rq2/reproduce_rq2_rep1/rq2_cot_fairness/developer/
results/rq2/reproduce_rq2_rep1/solar_rq2_cot_fairness/test_result/developer/scores_v1.json
```

These conditions separate CoT and fairness wording to avoid confounding their effects.

## 4. Reproduce RQ3: software-development workflows

**Twelve distinct configurations** cover three comparison groups:

| Comparison | Configurations |
| --- | --- |
| Workflow structure | `raw`, `waterfall`, `scrum` |
| Fairness-aware roles in Waterfall | `waterfall` baseline, `waterfall_pm_fair`, `waterfall_architect_fair`, `waterfall_developer_fair`, `waterfall_qa_fair`, `waterfall_all_fair` |
| Role ablations in Waterfall | `waterfall` baseline, `no_tester`, `no_architect_tester`, `no_requirement_tester`, `developer_only` |

`waterfall` is shared across groups and is generated **once per independent run**, not three times.

Run all 12 configurations sequentially, including Solar evaluation:

```bash
bash scripts/run_rq3_full.sh reproduce_rq3_rep1
```

Equivalent runner:

```bash
python commands/run_rq3_revision.py \
  --replicate-id reproduce_rq3_rep1 --start 0 --end 343 --evaluate
```

Example output locations:

```text
results/rq3_flowgen/reproduce_rq3_rep1__waterfall/final_code/
results/rq3_flowgen/reproduce_rq3_rep1__waterfall/solar/test_result/final/scores_v1.json
```

For a small subset, use `--start 0 --end 10` with the Python runner; `--end` is exclusive.

## 5. Reproduce RQ4: Fairness Monitor Agent

The FMA pipeline runs **from the original task**, not from a previously generated Developer output:

```text
Original task
  → Functional Requirements Analyst
  → Fairness Requirements Analyst
  → Developer
  → Round 1: Functional Review → Functional Repair if needed
             → Fairness Review → Fairness Repair if needed
  → Round 2: same sequence
  → Round 3: same sequence
```

**Current revision behavior:** Every round performs fresh functional and fairness reviews **even when a preceding round passes**. A repairer is called only when its reviewer reports issues. The fairness review uses the original task and code-level attribute evidence; upstream attribute labels are not treated as authoritative. Solar is an external evaluator and its feedback is **never supplied to the agents**.

Run all 343 tasks **fresh from end to end**, followed by Solar evaluation of the Developer baseline and all three rounds:

```bash
bash scripts/run_rq4_full.sh reproduce_rq4_rep1
```

Equivalent:

```bash
python commands/run_rq4_revision.py \
  --run-id reproduce_rq4_rep1 --start 0 --end 343 \
  --rounds 3 --temperature 0.8 --evaluate
```

Output examples:

```text
results/rq4/reproduce_rq4_rep1/functional_requirements/
results/rq4/reproduce_rq4_rep1/fairness_requirements/
results/rq4/reproduce_rq4_rep1/developer/
results/rq4/reproduce_rq4_rep1/round1/fairness_reviewer/
results/rq4/reproduce_rq4_rep1/round1/fairness_repairer/
results/rq4/reproduce_rq4_rep1/round2/fairness_repairer/
results/rq4/reproduce_rq4_rep1/round3/fairness_repairer/
results/rq4/reproduce_rq4_rep1/solar/test_result/developer/scores_v1.json
results/rq4/reproduce_rq4_rep1/solar/test_result/round1/scores_v1.json
results/rq4/reproduce_rq4_rep1/solar/test_result/round2/scores_v1.json
results/rq4/reproduce_rq4_rep1/solar/test_result/round3/scores_v1.json
```

**Do not use `--post-developer-only` for an independent fresh RQ4 run.** That option deliberately reuses upstream task artifacts for a targeted post-Developer experiment.

## 6. Repetitions and statistical analysis

RQ1 and RQ2 already generate five methods per task/condition. For RQ3 and RQ4, repeat the **entire pipeline** using distinct run IDs so that stochastic outputs are independent:

```bash
bash scripts/run_rq3_full.sh reproduce_rq3_rep2
bash scripts/run_rq3_full.sh reproduce_rq3_rep3

bash scripts/run_rq4_full.sh reproduce_rq4_rep2
bash scripts/run_rq4_full.sh reproduce_rq4_rep3
```

Report per-run results, the **mean and standard deviation** across runs, and uncertainty intervals when applicable. `analysis/bootstrap_cbs.py` can compute task-cluster bootstrap CIs from locally saved Solar `bias_info_files` for multiple complete repetitions. Examples:

```bash
python analysis/bootstrap_cbs.py \
  --roots results/rq3_flowgen/reproduce_rq3_rep1__waterfall/solar \
          results/rq3_flowgen/reproduce_rq3_rep2__waterfall/solar \
          results/rq3_flowgen/reproduce_rq3_rep3__waterfall/solar \
  --agent final

python analysis/bootstrap_cbs.py \
  --roots results/rq4/reproduce_rq4_rep1/solar \
          results/rq4/reproduce_rq4_rep2/solar \
          results/rq4/reproduce_rq4_rep3/solar \
  --agent round3 --before-agent developer
```

These examples assume Solar scores were saved in the **same project checkout** by the standard `--evaluate` runners. For evaluations done in independent worker clones, point `--roots` to the actual clone result directories or consolidate those outputs first.

## 7. Evaluating existing generated code with Solar

If a generation run has already completed, it can be evaluated **without calling the LLM again**. For example:

```bash
bash commands/evaluate_solar.sh \
  --response-dir results/rq4/reproduce_rq4_rep1/round3/fairness_repairer \
  --out-dir results/rq4/reproduce_rq4_rep1/solar \
  --label round3 --start 0 --end 343 --samples 1
```

For RQ1/RQ2, set `--samples 5` and select the corresponding Developer output directory. The script generates a local `fairness_test/test_suites/config.py` from `config_template.py`; **do not execute two Solar evaluations concurrently against the same working copy**, because they share that mutable file. Use independent repository/worker copies for parallel Solar evaluation.

Solar preserves compact score and bias/attribute summaries. By default it prunes very large raw test logs after scoring (`SOLAR_KEEP_RAW=0`). A generated score file contains the benchmark-level fairness/attribute metrics; separately report the executable denominator.

## 8. Previous completed revision runs (reference only)

The following IDs identify the **single complete runs** retained from the October 2026 revision campaign. They are not automatically downloaded with the Git repository.

- **RQ3:** `luna_rq3_full343` (12 configurations; paths use `results/rq3_flowgen/luna_rq3_full343__<configuration>/final_code/`).
- **RQ4:** `luna_rq4_fresh_endtoend_rep1` (complete fresh run from requirements through three review/repair rounds; `results/rq4/luna_rq4_fresh_endtoend_rep1/`). Only this final clean RQ4 run is intended for the archival results package.

The completed RQ3/RQ4 campaign used separate Solar worker clones (`~/PycharmProjects/solar_worker1` through `solar_worker7`) to evaluate stages/configurations in parallel. Consequently, **its Solar score files may reside in those worker directories, not in the corresponding project-level `results/` directories**. The archive/Drive snapshot is the place to retain those generated artifacts and scores. Do not mix these original run IDs with the new `reproduce_*` IDs above.

## 9. Resume, completeness, and cost

An interrupted generation run can generally be resumed with the **same run ID**; completed per-task files are skipped. For a genuinely new stochastic repetition, **always use a new ID**. Verify that each expected task has its output file and inspect errors before interpreting aggregate scores. Solar should be run only after generation is complete.

API usage and cost are recorded locally:

```bash
python scripts/summarize_usage.py
```

The underlying usage log is `results/api_usage.jsonl` and may contain operational metadata; keep it in a private experiment archive rather than automatically publishing it.

## 10. Functional correctness and evaluation limits

The 343 Solar test suites evaluate specified *fairness metamorphic relations* and attribute-use behavior of generated methods. Exhaustive execution of the test cases encoded in a suite can detect violations **within that specified test space**; it does not establish that every possible input or the intended eligibility decision is implemented correctly. In particular, a method that always returns `True` could avoid a fairness inconsistency while violating the task's actual decision logic.

Many benchmark tasks do not state a unique policy or threshold, so a complete reference functional oracle cannot be inferred without adding new semantics. **Executable rate**, **Pass@attribute**, and **CBS** must therefore be reported as distinct measures. Do not claim full semantic functional correctness from them alone. `docs/FUNCTIONAL_CORRECTNESS_PLAN.md` discusses optional stronger validation and the alternative of narrowing functional-correctness claims.

Solar measures the benchmark's operational fairness definition, including its explicitly designated sensitive attributes. Task-specific functional relevance and benchmark-designated sensitivity can disagree; report and discuss such disagreements instead of silently modifying the benchmark or hardcoding Solar attributes into FMA.

## 11. Reproducibility, security, and provenance

- `dataset/prompts.jsonl`, `fairness_test/test_suites/`, RQ runners, and workflow JSON files are required reproducibility inputs.
- `fairness_test/test_suites/config.py` is machine-generated; the tracked `config_template.py` is the source template.
- Do **not** commit `.env`, credentials, generated `results/`, caches, large raw logs, or local worker archives.
- The original FlowGen hand-off is documented in `docs/FLOWGEN_HANDOFF_AUDIT.md`. Some earlier files and staged experiment plans describe historical behavior; the current revised RQ4 run uses the **fresh-review-per-round** pipeline described in this README.
- Use the Git revision and model configuration from the actual run for exact provenance. Model/API behavior and non-deterministic generations may vary over time.

For additional details, see `docs/EXPERIMENT_RUNBOOK.md`, `docs/RQ3_ABLATION_IMPLEMENTATION.md`, and `docs/FUNCTIONAL_CORRECTNESS_PLAN.md`.
