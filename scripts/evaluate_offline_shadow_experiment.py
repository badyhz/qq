#!/usr/bin/env python3
"""CLI for offline shadow experiment evaluation.

Usage:
    python scripts/evaluate_offline_shadow_experiment.py \
        --matrix-json PATH \
        --fixture-dir PATH \
        --output-json PATH \
        --output-md PATH

Exit 0 on success.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.offline_shadow_evaluator import evaluate_experiment


def _render_markdown(result: dict) -> str:
    lines = [
        f"# Experiment: {result.get('experiment_id', 'unknown')}",
        "",
        f"**Runs evaluated:** {result.get('run_count', 0)}",
        "",
    ]
    for run in result.get("runs", []):
        m = run.get("metrics", {})
        lines.append(f"## Run: {run.get('run_id', '?')}")
        lines.append("")
        lines.append(f"- Outcomes loaded: {run.get('outcome_count', 0)}")
        lines.append(f"- Candidates: {m.get('candidate_count', 0)}")
        lines.append(f"- Win rate: {m.get('win_rate', 0):.4f}")
        lines.append(f"- Expectancy R: {m.get('expectancy_r', 0):.4f}")
        lines.append(f"- Max drawdown R: {m.get('max_drawdown_r', 0):.4f}")
        lines.append(f"- Profit factor: {m.get('profit_factor', 0):.4f}")
        lines.append(f"- Sample quality: {m.get('sample_quality_score', 0):.4f}")
        lines.append(f"- Coverage: {m.get('coverage_status', 'unknown')}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate offline shadow experiment"
    )
    parser.add_argument("--matrix-json", required=True, help="Path to experiment matrix JSON")
    parser.add_argument("--fixture-dir", required=True, help="Path to outcome fixture directory")
    parser.add_argument("--output-json", required=True, help="Path for JSON output")
    parser.add_argument("--output-md", required=True, help="Path for Markdown output")
    args = parser.parse_args()

    matrix_path = Path(args.matrix_json)
    if not matrix_path.exists():
        print(f"ERROR: matrix file not found: {matrix_path}", file=sys.stderr)
        return 1

    try:
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot read matrix: {exc}", file=sys.stderr)
        return 1

    result = evaluate_experiment(matrix, args.fixture_dir)

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(_render_markdown(result), encoding="utf-8")

    print(f"Evaluated {result['run_count']} runs -> {args.output_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
