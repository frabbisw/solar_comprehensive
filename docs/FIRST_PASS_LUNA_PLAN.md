# First complete GPT-6 Luna pass

All new GPT-6 Luna experiments use `OPENAI_REASONING_EFFORT=none`.
RQ1 varies temperature; RQ2/RQ3/RQ4 use the common anchor temperature 0.8.

## 1. RQ1: full temperature sweep

```bash
bash scripts/run_rq1_full.sh luna_rq1_run1
```

Runs 343 tasks x 5 independent generations at each of 5 temperatures
(0.2, 0.4, 0.6, 0.8, 1.0): 8,575 Luna generations.

## 2. RQ4: one complete FMA run

```bash
bash scripts/run_rq4_once.sh luna_rq4_run1
```

Runs all 343 tasks through Developer and up to three FMA repair rounds.

## 3. RQ3: five-task pilot

```bash
bash scripts/run_rq3_sample_once.sh luna_rq3_pilot5_run1 5
```

Runs tasks 0-4 through all 12 RQ3 configurations.

## 4. RQ3: one full run

```bash
bash scripts/run_rq3_once.sh luna_rq3_run1
```

Runs all 343 tasks through all 12 configurations once.

## 5. RQ2: all six revision prompt conditions

```bash
bash scripts/run_rq2_once.sh luna_rq2_run1 luna_rq1_run1
```

Conditions: Default, Pure CoT, fairness-only, positive-role-only,
CoT+fairness, and positive-role+CoT+fairness.  RQ2 Default reuses the exact
Luna outputs already generated for RQ1 at t=0.8, because the two default
system prompts are identical.  Therefore this command makes 8,575 new Luna
generations rather than duplicating another 1,715 calls.

## Usage report

```bash
python scripts/summarize_usage.py
```
