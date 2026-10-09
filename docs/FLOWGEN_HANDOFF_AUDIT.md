# FlowGen hand-off audit

This note records what was actually present in `code_FlowGen.zip` before any revision cleanup. It is intended to prevent accidental mixing of historical artifacts with the new rebuttal runs.

## What was present

- The archive contained 44,451 entries and about 900 MB uncompressed data.
- Most of that size was two bundled Python virtual environments (`workflow/Lib` and `code/workflow/Lib`). These are not needed for reproducibility and were not copied into the clean revision tree.
- The executable source was under `code_FlowGen/code/`.
- The main script was hard-coded to `prompts_7.jsonl` and `waterfall_solar/waterfall_solar.json`, so it was not a safe entry point for a full 343-task rerun.
- The OpenAI implementation used the obsolete `openai.ChatCompletion` interface from OpenAI Python 0.28.x.

## Security issue found

`code_FlowGen/code/conf.json` contained plaintext provider API credentials. They were deliberately **not copied** into this clean tree. The credentials from the original archive should be revoked/rotated before any further work.

## Historical result coverage found in the archive

Full-dataset workspace logs:

- `workspace_backup/dataset/gpt_raw`: 343/343 tasks.
- `workspace_backup/dataset/waterfall`: 343/343 tasks.

The following configurations had only a common 70-task subset in the hand-off:

- raw GPT subset
- Scrum
- Waterfall + PM fairness instruction
- Waterfall + Architect fairness instruction
- Waterfall + Developer fairness instruction
- Waterfall + QA fairness instruction
- Waterfall + all-role fairness instruction
- `waterfall_test`

The 70 task IDs are:

`0-9, 51-60, 102-111, 152-161, 203-212, 263-272, 293-302`.

Therefore, the hand-off itself does **not** contain a 343-task Scrum run or 343-task role-prompting runs.

## Fairness-prompt ambiguity in the historical Waterfall artifacts

The full 343-task `dataset/waterfall` logs already contain the sentence
`You should consider fairness to avoid social bias.` in the QA test-case prompt.
By contrast, the 70-task `subset/waterfall_test` logs use the same QA template without that sentence.

This makes it unsafe to treat the full historical Waterfall artifact as an unambiguous "no fairness instruction" baseline for a new revision. The clean runner therefore removes the hard-coded fairness sentence from the base template and controls it explicitly with:

`--fairness-role none|product_manager|architect|developer|qa|all`

The injected sentence is the same sentence found in the historical role-level runs.

## Role-ablation artifacts

The hand-off did not contain an identifiable complete set of artifacts/code variants corresponding to all role-ablation rows currently described in the manuscript (no tester, no architect + tester, no requirement engineer + tester, developer only). The original experimenter no longer has additional files. For the revision, these four variants are therefore **reconstructed explicitly from the manuscript role-removal definition** and documented in `docs/RQ3_ABLATION_IMPLEMENTATION.md`. They must be described as reconstructed revision configurations, not as recovered historical source.

## Revision cleanup performed

The clean `flowgen/` directory contains only:

- source code,
- prompt templates,
- workflow JSON files,
- a new safe runner (`run_flowgen.py`), and
- a modern OpenAI Responses API gateway using the root `.env` configuration.

No virtual environment, IDE state, cache files, old API keys, or large legacy workspaces are bundled.
