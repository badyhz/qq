#!/usr/bin/env python3
"""CLI for offline shadow scorecard generation.

Usage:
    python scripts/generate_offline_shadow_scorecard.py \
        --results-json PATH \
        --output-json PATH

Exit 0 on success.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.offline_shadow_scorecard import grade_experiment


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate offline shadow scorecard"
    )
    parser.add_argument("--results-json", required=True, help="Path to evaluator results JSON")
    parser.add_argument("--output-json", required=True, help="Path for scorecard JSON output")
    args = parser.parse_args()

    results_path = Path(args.results_json)
    if not results_path.exists():
        print(f"ERROR: results file not found: {results_path}", file=sys.stderr)
        return 1

    try:
        results = json.loads(results_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot read results: {exc}", file=sys.stderr)
        return 1

    scorecard = grade_experiment(results)

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(scorecard, indent=2, default=str), encoding="utf-8")

    print(
        f"Scorecard: verdict={scorecard['verdict']} "
        f"PASS={scorecard['pass_count']} "
        f"WATCH={scorecard['watch_count']} "
        f"REJECT={scorecard['reject_count']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
