# Fairness Agent – Codebase Guide

## Folder structure

```
fairness_agent/
│
├── dataset/
│   └── prompts_1.jsonl               ← SocialBias-Bench (343 tasks)
│
├── agents/                           ← Standard pipeline agents
│   ├── requirements.py               ← Requirement engineer (multi-agent Exp 2)
│   ├── developer.py                  ← Code generation (Exp 1 & 3)
│   ├── test_agent.py                 ← Test role stub (multi-agent ablations)
│   ├── reviewer.py                   ← Legacy reviewer (oracle-dependent, Exp 2)
│   └── repairer.py                   ← Legacy repairer (natural-language instruction)
│
├── fma/                              ← Fairness Monitor Agent (Exp 3)
│   ├── bias_aware_requirements.py    ← Stage 0: Fairness Requirement Analyst (optional)
│   ├── bias_aware_reviewer.py        ← Stage 2: Oracle-free fault reporter
│   ├── bias_repairer.py              ← Stage 3: Full method rewrite from fault report
│   └── bias_verifier.py              ← Stage 4: Post-repair sanity check (optional)
│
├── shared/                           ← Common utilities
│   ├── llm_client.py                 ← Single LLM gateway (add new models here)
│   ├── io_utils.py                   ← JSONL I/O, code cleaning, path helpers
│   └── base_agent.py                 ← Abstract base class (CLI + iteration loop)
│
├── commands/
│   └── run_pipeline.sh               ← Unified orchestrator for Exp 1 / 2 / 3
│
├── results/                          ← Created at runtime
│   ├── exp1_default/developer/       ← Exp 1 default output → feed to Solar
│   ├── exp1_chain_of_thoughts/       ← Exp 1 CoT output
│   ├── exp1_positive_chain_of_thoughts/
│   ├── exp2_legacy/
│   │   ├── developer/
│   │   ├── reviewer/
│   │   └── repairer/                 ← Exp 2 final output → feed to Solar
│   └── exp3_fma/
│       ├── spec/                     ← Stage 0 fairness specs (if --with_spec)
│       ├── developer/                ← Stage 1 generated code
│       ├── reviewer/                 ← Stage 2 fault reports
│       ├── repairer/                 ← Stage 3 repaired code → feed to Solar
│       └── verifier/                 ← Stage 4 verification (if --verify)
│
└── .env                              ← API keys (never commit)
```

---

## Environment setup

```bash
conda activate fagent
pip install openai python-dotenv

# .env in repo root:
echo "OPENAI_API_KEY=sk-..." > .env
```

---

## Experiment 1 – Single-prompt baselines (default / CoT / P-CoT)

```bash
# Default (no mitigation)
bash commands/run_pipeline.sh --exp 1 --style default

# Chain-of-Thought
bash commands/run_pipeline.sh --exp 1 --style chain_of_thoughts

# Positive Role + CoT
bash commands/run_pipeline.sh --exp 1 --style positive_chain_of_thoughts

# Smoke test (5 tasks)
bash commands/run_pipeline.sh --exp 1 --style default --start 0 --end 5
```

Feed Solar the output: `results/exp1_<style>/developer/`

---

## Experiment 2 – Legacy multi-agent (oracle-dependent)

Requires Solar's `bias_info` and `related_info` files to already exist
(run Solar's evaluation on the Exp 1 default output first).

```bash
bash commands/run_pipeline.sh --exp 2 \
    --bias_dir    results/solar/bias_info \
    --related_dir results/solar/related_info
```

Feed Solar the output: `results/exp2_legacy/repairer/`

---

## Experiment 3 – FMA (oracle-free, main contribution)

### Minimal (no upstream spec, no verifier)
```bash
bash commands/run_pipeline.sh --exp 3
```

### With upstream Fairness Requirement Analyst
```bash
bash commands/run_pipeline.sh --exp 3 --with_spec
```

### Full pipeline (spec + verifier)
```bash
bash commands/run_pipeline.sh --exp 3 --with_spec --verify
```

### Smoke test (first 5 tasks)
```bash
bash commands/run_pipeline.sh --exp 3 --start 0 --end 5
```

### Multi-round repair (up to 3 rounds)
```bash
bash commands/run_pipeline.sh --exp 3 --rounds 3
```

Feed Solar the output: `results/exp3_fma/repairer/`

---

## File formats

### Input – `prompts_1.jsonl`
```json
{"task_id": "0", "prompt": "from dataclasses import dataclass\n\n@dataclass\nclass Person:\n    ..."}
```

### Developer / Repairer output – `task_N_generated_code.jsonl`
```json
{"generated_code": "def qualified_for_financial_aid(self) -> bool:\n    ..."}
```
Repairer adds: `"repaired": true/false, "rounds": 1`

### FMA Reviewer output – `task_N_review.jsonl`
```json
{
  "false_inclusions": ["gender", "race"],
  "false_exclusions": ["income"],
  "reasoning": "The method checks self.gender but the task only requires income.",
  "pass": false
}
```

### Fairness Spec output – `task_N_requirements.jsonl`
```json
{
  "required_attributes": ["income"],
  "prohibited_attributes": ["gender", "race", "religion", "age", "marital_status", "employment_status", "education"],
  "rationale": "The task grants financial aid based on income alone."
}
```

---

## Key design decisions

| Decision | Rationale |
|---|---|
| `shared/llm_client.py` is the single gateway | Adding a new model requires one change in one file |
| `BaseAgent` handles CLI + iteration loop | Each agent only implements `process_task()` |
| FMA Reviewer is oracle-free | No Solar `bias_info` required → works on any dataset |
| Repairer does full rewrites | No fragile JSON substring matching |
| `pass` short-circuits repair | Zero extra LLM calls for clean samples |
| Reviewer + Repairer temperature = 0.0 | Deterministic fault localization and repair |
| `--with_spec` is optional | FMA works with or without the upstream spec agent |
| `--verify` is optional | Cheap pre-Solar filter; not a replacement for Solar |
| Max 3 repair rounds | Per ChatRepair (ISSTA 2024) / Self-Refine (NeurIPS 2023) |
