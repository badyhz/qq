#!/usr/bin/env python3
"""Render research comparison report from existing comparison artifacts.

Usage:
    python3 scripts/render_research_comparison_report.py \
        --comparison-dir /tmp/research_comparison_analytics \
        --output-dir /tmp/research_comparison_report_rendered

Safety: offline only. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.research_comparison_report import (
    render_comparison_html,
    render_comparison_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render research comparison report")
    parser.add_argument("--comparison-dir", required=True, help="Comparison artifacts directory")
    parser.add_argument("--output-dir", required=True, help="Output directory for rendered reports")
    args = parser.parse_args()

    comparison_dir = Path(args.comparison_dir)
    if not comparison_dir.exists():
        print(f"FAIL: comparison directory missing: {comparison_dir}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load comparison artifacts
    scorecard = _load_json(comparison_dir / "comparison_scorecard.json")
    metrics = _load_json(comparison_dir / "extracted_metrics.json")
    pairwise = _load_json(comparison_dir / "pairwise_comparison.json")
    trend = _load_json(comparison_dir / "trend_report.json")
    regression = _load_json(comparison_dir / "regression_report.json")
    manifest = _load_json(comparison_dir / "research_comparison_manifest.json")

    # Validate required artifacts exist
    errors = []
    if not scorecard:
        errors.append("comparison_scorecard.json missing or empty")
    if not metrics:
        errors.append("extracted_metrics.json missing or empty")
    if not pairwise:
        errors.append("pairwise_comparison.json missing or empty")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 2

    # Render markdown
    md_report = render_comparison_markdown(
        scorecard, metrics, pairwise, trend, regression, manifest,
    )
    (output_dir / "research_comparison_report.md").write_text(md_report)

    # Render HTML
    html_report = render_comparison_html(
        scorecard, metrics, pairwise, trend, regression, manifest,
    )
    (output_dir / "research_comparison_report.html").write_text(html_report)

    print(f"PASS: rendered md={len(md_report)} chars, html={len(html_report)} chars")
    return 0


def _load_json(path: Path) -> dict:
    """Load JSON file, return empty dict on failure."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}


if __name__ == "__main__":
    sys.exit(main())
