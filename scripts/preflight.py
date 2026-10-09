#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def ok(msg): print("[OK]  ", msg)
def warn(msg): print("[WARN]", msg)
def fail(msg): print("[FAIL]", msg); return False


passed = True
model = os.getenv("OPENAI_MODEL", "gpt-6-luna").strip()
effort = os.getenv("OPENAI_REASONING_EFFORT", "none").strip().lower()
common_temp = os.getenv("REVISION_COMMON_TEMPERATURE", "0.8").strip()
flow_temp = os.getenv("FLOWGEN_TEMPERATURE", common_temp).strip()
key = os.getenv("OPENAI_API_KEY", "")

ok(f"OPENAI_MODEL={model}")
ok(f"OPENAI_REASONING_EFFORT={effort}")
ok(f"REVISION_COMMON_TEMPERATURE={common_temp}")
ok(f"FLOWGEN_TEMPERATURE={flow_temp}")
if key:
    ok("OPENAI_API_KEY is set (value hidden)")
else:
    warn("OPENAI_API_KEY is not set. Static checks can run; API smoke tests cannot.")

# One reasoning configuration across all RQs is deliberate. RQ1 varies
# temperature, so reasoning must be disabled for the common configuration.
if effort != "none":
    passed = fail(
        "For the planned same-configuration RQ1-RQ4 campaign, set "
        "OPENAI_REASONING_EFFORT=none. RQ1 varies temperature."
    ) and passed
else:
    ok("Same reasoning configuration is compatible with the RQ1 temperature sweep")

try:
    if abs(float(common_temp) - float(flow_temp)) > 1e-12:
        warn("FLOWGEN_TEMPERATURE differs from REVISION_COMMON_TEMPERATURE")
    else:
        ok("RQ2/RQ3/RQ4 share the same anchor temperature")
except ValueError:
    passed = fail("Temperature environment values must be numeric") and passed

prompts = ROOT / "dataset" / "prompts.jsonl"
try:
    rows = [json.loads(x) for x in prompts.read_text(encoding="utf8").splitlines() if x.strip()]
    ids = [str(r.get("task_id")) for r in rows]
    if len(rows) == 343 and ids == [str(i) for i in range(343)]:
        ok("dataset/prompts.jsonl has 343 tasks with IDs 0..342")
    else:
        passed = fail(f"dataset/prompts.jsonl unexpected shape: {len(rows)} rows") and passed
except Exception as exc:
    passed = fail(f"cannot read prompts: {exc}") and passed

required = [
    "agents/developer.py",
    "agents_full/requirements.py",
    "agents_full/reviewer.py",
    "agents_full/repairer.py",
    "fma_full/bias_aware_requirements.py",
    "fma_full/bias_aware_reviewer.py",
    "fma_full/bias_repairer.py",
    "fairness_test/test_suites/test_suite_0.py",
    "flowgen/run_flowgen.py",
    "flowgen/utils/json_utils.py",
    "flowgen/workflow/rawGPT/rawGPT.json",
    "flowgen/workflow/waterfall/waterfall.json",
    "flowgen/workflow/scrum/scrum.json",
    "flowgen/workflow/ablations/no_tester.json",
    "flowgen/workflow/ablations/no_architect_tester.json",
    "flowgen/workflow/ablations/no_requirement_tester.json",
    "flowgen/workflow/ablations/developer_only.json",
    "commands/run_rq1_revision.py",
    "commands/run_rq2_revision.py",
    "commands/run_rq3_revision.py",
    "commands/run_rq4_revision.py",
    "scripts/run_rq1_full.sh",
    "scripts/run_rq2_once.sh",
    "scripts/run_rq1_anchor_once.sh",
    "scripts/run_rq1_remaining_temperatures.sh",
    "scripts/run_rq3_sample_once.sh",
    "scripts/run_rq3_once.sh",
    "scripts/run_rq4_once.sh",
]
for rel in required:
    p = ROOT / rel
    if p.exists(): ok(rel)
    else: passed = fail(f"missing {rel}") and passed

# Validate the full 12-configuration RQ3 matrix without importing API clients.
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_flowgen", ROOT / "flowgen" / "run_flowgen.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    expected = {
        "raw", "waterfall", "scrum",
        "waterfall_pm_fair", "waterfall_architect_fair", "waterfall_developer_fair",
        "waterfall_qa_fair", "waterfall_all_fair",
        "no_tester", "no_architect_tester", "no_requirement_tester", "developer_only",
    }
    if set(mod.CONFIGS) == expected:
        ok("RQ3 matrix contains all 12 unique manuscript configurations")
    else:
        passed = fail(f"RQ3 configuration mismatch: {sorted(mod.CONFIGS)}") and passed
    for name, cfg in mod.CONFIGS.items():
        wf = ROOT / "flowgen" / "workflow" / cfg["workflow"]
        json.loads(wf.read_text(encoding="utf-8"))
    ok("All RQ3 workflow JSON files parse successfully")
except Exception as exc:
    passed = fail(f"RQ3 matrix validation failed: {exc}") and passed

# RQ1 Default and RQ2 Default must be byte-for-byte identical so the
# RQ1 t=0.8 outputs can serve as the RQ2 baseline without duplicate calls.
try:
    import ast
    tree = ast.parse((ROOT / "agents" / "developer.py").read_text(encoding="utf-8"))
    styles = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PROMPT_STYLES" for t in node.targets):
            styles = ast.literal_eval(node.value)["gpt"]
            break
    if styles is None:
        passed = fail("PROMPT_STYLES not found in agents/developer.py") and passed
    elif styles["default"] == styles["rq2_default"]:
        ok("RQ1 Default and RQ2 Default prompts are identical")
    else:
        passed = fail("RQ1 Default and RQ2 Default prompts differ") and passed
except Exception as exc:
    passed = fail(f"Could not validate RQ1/RQ2 default prompts: {exc}") and passed

# Guard against accidentally reintroducing different temperatures inside FMA.
hardcoded = []
for rel in [
    "agents_full/requirements.py", "agents_full/developer.py",
    "agents_full/reviewer.py", "agents_full/repairer.py",
    "fma_full/bias_aware_requirements.py", "fma_full/bias_aware_reviewer.py",
    "fma_full/bias_repairer.py",
]:
    text = (ROOT / rel).read_text(encoding="utf-8")
    if "temperature=0.0" in text or "temperature = 0.0" in text:
        hardcoded.append(rel)
if hardcoded:
    passed = fail(f"Hard-coded 0.0 temperature remains in: {hardcoded}") and passed
else:
    ok("RQ4 agents use the run-level temperature rather than hidden 0.0 overrides")

print("\nPreflight", "PASSED" if passed else "FAILED")
raise SystemExit(0 if passed else 1)
