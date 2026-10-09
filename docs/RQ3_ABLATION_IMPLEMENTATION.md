# RQ3 role-ablation reconstruction for the EMSE revision

The handed-over 2025 FlowGen archive does **not** contain identifiable source variants for the four role-ablation rows described in the manuscript. The revision therefore reconstructs those configurations directly from the manuscript definition instead of pretending that missing historical code was recovered.

The manuscript describes a Waterfall pipeline with four conceptual roles: requirement engineering, architecture, development, and testing. In the handed-over FlowGen implementation, the requirement-engineering role is named **Product Manager**. The clean baseline is:

1. Product Manager / requirement engineering
2. Architect
3. Developer
4. Quality Assurance / tester

The following ablations are now implemented.

## `no_tester`

Retained roles: Product Manager, Architect, Developer.

- The Testing and Bugfix stage is removed completely.
- Review-meeting prompts are also filtered so that the removed Tester is not silently simulated inside another LLM call.
- The final artifact is the Developer's revised code (`Code0Revise`).

## `no_architect_tester`

Retained roles: Product Manager, Developer.

- Architect and Testing stages are removed.
- Cross-role review calls requiring Architect/Tester are removed.
- The Product Manager produces the PRD draft.
- Because there is no Architect artifact, the Developer receives the PRD directly.
- The Developer produces the final code without an Architect/Tester code-review meeting.

## `no_requirement_tester`

Retained roles: Architect, Developer.

- Product Manager / requirement-engineering and Testing stages are removed.
- The raw task is seeded into the workspace, so the Architect receives the original task directly when no PRD exists.
- Design review retains only the Developer voice; Tester is removed.
- Code review retains only the Architect voice; Tester is removed.
- The final artifact is the Developer's revised code.

## `developer_only`

Retained role: Developer only.

- Product Manager, Architect, and Testing stages are removed.
- The Developer receives the raw task directly.
- No cross-role review meeting is retained, because every reviewer in the original code-review template belongs to a removed role.
- The Developer's first generated code artifact (`Code0Draft`) is the final output.

## Why review-meeting prompts are filtered

The historical FlowGen implementation uses some single LLM calls to simulate suggestions from multiple roles. For example, its code-review prompt asks the model to act as both an Architect and a Tester. If only the top-level workflow stage were removed, an ablated role would still influence the result through these embedded review prompts. The revision therefore removes those simulated voices too, so a role ablation means that the named role is actually absent from the pipeline.

## Historical-vs-revision distinction

These four ablations are **reconstructed revision configurations** based on the manuscript description. They are not claimed to be recovered copies of the missing 2025 ablation source. The revision replication package should state this transparently.
