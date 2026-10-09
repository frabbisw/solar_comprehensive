# Stronger functional-correctness validation: what the current benchmark can and cannot support

Reviewer 2 correctly points out that Pass@attribute is an attribute-usage metric, not a full logical-correctness oracle.

The current SocialBias-Bench task definitions do not contain a unique expected Boolean decision rule for many tasks. For example, a task can ask whether a person is qualified for financial aid and identify income as task-related, but the prompt does not specify a canonical income threshold or complete policy. Therefore, an automatic script cannot truthfully derive exact expected outputs for all 343 tasks from the existing benchmark alone.

For that reason, the revision code does **not** silently invent a ground truth and does not relabel Pass@attribute as full functional correctness.

Two defensible revision options are:

1. **Narrow the claim.** Rename/reframe Pass@attribute as attribute-level task alignment and explicitly state that it is not full functional correctness.
2. **Add a new manually adjudicated executable-oracle study.** Use a documented subset, define an explicit intended policy/reference implementation for each selected task, have at least two researchers review/adjudicate those policies, and execute generated methods against those reference tests.

A convenient 70-task subset already present in the historical FlowGen hand-off contains ten tasks from each contiguous benchmark category:

- 0-9
- 51-60
- 102-111
- 152-161
- 203-212
- 263-272
- 293-302

If the stronger study is added, preserve the original benchmark prompts for the LLM experiments. The manually written oracle should be used **only for external post-hoc evaluation**, so it cannot leak additional decision rules into generation.

This issue should be resolved before making any revised claim such as "FMA improves functional correctness." Until then, the defensible phrasing is that FMA improves **Pass@attribute / attribute-level task alignment**.
