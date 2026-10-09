RQ4 FMA: Generic independent reviews in all three rounds

Installation: From the project root, first back up four existing files, then
unzip rq4_three_rounds_generic_patch.zip in the project root.

Files replaced:
  agents_full/reviewer.py
  agents_full/repairer.py
  fma_full/bias_aware_reviewer.py
  fma_full/bias_repairer.py

Changes:
- Functional and fairness reviewers evaluate code in R1, R2, and R3 even if a
  previous round passed or an older upstream file said fma_converged=True.
- Repairs still run ONLY when the matching reviewer reports actionable issues.
- A clean fairness review preserves the candidate but does not set convergence.
- Fairness reviewer sees original task + generated method + mechanically
  extracted self.field attributes; earlier required/restricted classifications
  are not supplied to it, avoiding anchoring to potentially incorrect labels.
- All four agents retain their original generic SYSTEM_PROMPT strings.
- No Solar outputs or protected-attribute lists enter agent prompts.
- Runner/Developer/upstream requirements and Solar evaluation remain unchanged.

Known limitation: Functional and fairness repairs can disagree, as observed for
Task 246. This patch does not resolve that conflict or guarantee CBS improvement.
Always use a NEW run-id, because existing per-stage output files are skipped.

Validation: Python compile + offline three-round simulation with mocked LLM
passed: 3 functional reviews, 3 fairness reviews, and repair only when the
third fairness review found an issue. No API calls in validation.
