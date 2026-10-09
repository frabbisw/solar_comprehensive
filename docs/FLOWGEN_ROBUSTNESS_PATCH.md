# FlowGen robustness patch for the 2026 revision

The 2025 FlowGen hand-off assumed that JSON-mode responses were returned as a
bare JSON object and that a repair attempt always changed the code. GPT-6 Luna
exposed two compatibility failures during the first live smoke test:

1. a valid repair JSON object could be followed by harmless extra text, causing
   `json.loads()` to fail with `JSONDecodeError: Extra data`;
2. if the model returned the same already-usable code for three repair attempts,
   FlowGen raised `Can not repair code` and treated the QA refinement as fatal.

The revision package now:

- extracts the first valid JSON object from a response while leaving its content
  unchanged;
- retries malformed/no-change repair responses up to the historical maximum of
  three attempts;
- if all attempts make no progress, carries the latest valid code forward and
  records `RepairStatus... = no_progress_fallback` rather than inventing a new
  repair or discarding usable code;
- applies the same robust JSON parsing to Scrum planning/review artifacts;
- retains FlowGen step-error recording for genuine unexpected failures.

This is a compatibility/robustness change, not a fairness intervention. It does
not add attributes, thresholds, fairness rules, or code edits to model output.
The raw responses and repair status remain in each FlowGen workspace log for
auditability.
