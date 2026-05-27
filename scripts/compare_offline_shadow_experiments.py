#!/usr/bin/env python3
"""CLI for offline shadow experiment comparison.

Usage:
    python scripts/compare_offline_shadow_experiments.py \
        --result-a PATH \
        --result-b PATH \
        --output-json PATH

Exit 0 on success.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.offline_shadow_comparison import compare_experiments


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two offline shadow experiments"
    )
    parser.add_argument("--result-a", required=True, help="Path to baseline results JSON")
    parser.add_argument("--result-b", required=True, help="Path to candidate results JSON")
    parser.add_argument("--output-json", required=True, help="Path for comparison JSON output")
    args = parser.parse_args()

    for label, path_str in [("result-a", args.result_a), ("result-b", args.result_b)]:
        p = Path(path_str)
        if not p.exists():
            print(f"ERROR: {label} file not found: {p}", file=sys.stderr)
            return 1

    try:
        result_a = json.loads(Path(args.result_a).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot read result-a: {exc}", file=sys.stderr)
        return 1

    try:
        result_b = json.loads(Path(args.result_b).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot read result-b: {exc}", file=sys.stderr)
        return 1

    comparison = compare_experiments(result_a, result_b)

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(comparison, indent=2, default=str), encoding="utf-8")

    print(
        f"Comparison: improved={comparison['improved']} "
        f"expectancy_delta={comparison['deltas']['expectancy_r']:.4f} "
        f"gate={comparison['gate_status_a']}->{comparison['gate_status_b']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
