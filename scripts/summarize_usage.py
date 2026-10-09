#!/usr/bin/env python3
"""Summarize API usage logged by the revision runners.

Defaults use GPT-6 Luna Standard short-context prices current when this revision
package was prepared. Override prices through environment variables if OpenAI
pricing changes before the final campaign.

Reasoning tokens are already included in output_tokens by the Responses API and
are therefore reported separately for visibility but NOT double-counted.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path


def fenv(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--usage-log", default=os.getenv("OPENAI_USAGE_LOG", "results/api_usage.jsonl"))
    ap.add_argument("--input-per-million", type=float, default=fenv("PRICE_INPUT_PER_M", "0.10"))
    ap.add_argument("--cached-input-per-million", type=float, default=fenv("PRICE_CACHED_INPUT_PER_M", "0.01"))
    ap.add_argument("--output-per-million", type=float, default=fenv("PRICE_OUTPUT_PER_M", "0.50"))
    args = ap.parse_args()

    path = Path(args.usage_log)
    if not path.exists():
        print(f"No usage log found: {path}")
        return 0

    groups = defaultdict(lambda: {"calls": 0, "input": 0, "cached": 0, "output": 0, "reasoning": 0})
    total = {"calls": 0, "input": 0, "cached": 0, "output": 0, "reasoning": 0}

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        context = r.get("experiment_context") or r.get("component") or "unknown"
        # Group by high-level RQ prefix when available.
        group = context.split(":", 1)[0] if ":" in context else context
        vals = {
            "calls": 1,
            "input": int(r.get("input_tokens", 0) or 0),
            "cached": int(r.get("cached_input_tokens", 0) or 0),
            "output": int(r.get("output_tokens", 0) or 0),
            "reasoning": int(r.get("reasoning_tokens", 0) or 0),
        }
        for k, v in vals.items():
            groups[group][k] += v
            total[k] += v

    def cost(x):
        uncached = max(0, x["input"] - x["cached"])
        return (
            uncached / 1_000_000 * args.input_per_million
            + x["cached"] / 1_000_000 * args.cached_input_per_million
            + x["output"] / 1_000_000 * args.output_per_million
        )

    print("API usage summary")
    print(f"Pricing used: input ${args.input_per_million}/M, cached ${args.cached_input_per_million}/M, output ${args.output_per_million}/M")
    print()
    print(f"{'Group':<12} {'Calls':>9} {'Input':>13} {'Cached':>13} {'Output':>13} {'Reasoning':>13} {'Est. USD':>10}")
    for group in sorted(groups):
        x = groups[group]
        print(f"{group:<12} {x['calls']:>9,} {x['input']:>13,} {x['cached']:>13,} {x['output']:>13,} {x['reasoning']:>13,} {cost(x):>10.2f}")
    print("-" * 88)
    print(f"{'TOTAL':<12} {total['calls']:>9,} {total['input']:>13,} {total['cached']:>13,} {total['output']:>13,} {total['reasoning']:>13,} {cost(total):>10.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
