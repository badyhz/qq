#!/usr/bin/env python3
"""Generate research quality closeout report.

Usage:
    python3 scripts/generate_research_quality_closeout.py \
        --quality-dir /tmp/multi_strategy_research_quality_gate \
        --output docs/dev_reports/t5201_t9000_research_quality_gate_closeout.md \
        --verdict PASS

Safety: offline only, no network, no promotion.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.research_quality_closeout import generate_closeout_report, build_closeout_data
from core.research_quality_contract import RELEASE_HOLD_VALUE, SAFETY_FLAGS
from core.research_quality_manifest import REQUIRED_ARTIFACTS


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate research quality closeout")
    parser.add_argument("--quality-dir", required=True, help="Quality gate output directory")
    parser.add_argument("--output", required=True, help="Output markdown path")
    parser.add_argument("--verdict", required=True, choices=["PASS", "PARTIAL", "FAIL"])
    parser.add_argument("--seed", type=int, default=424242)
    args = parser.parse_args()

    quality_dir = Path(args.quality_dir)
    if not quality_dir.exists():
        print(f"FAIL: quality directory missing: {quality_dir}", file=sys.stderr)
        return 2

    # Collect artifacts
    artifacts = [a for a in REQUIRED_ARTIFACTS if (quality_dir / a).exists()]

    # Load quality summary if available
    test_summary = {}
    acceptance_results = {}
    summary_path = quality_dir / "quality_gate_summary.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text())
            test_summary = summary.get("summary", {})
        except (json.JSONDecodeError, ValueError):
            pass

    # Generate closeout
    report = generate_closeout_report(
        verdict=args.verdict,
        seed=args.seed,
        artifacts=artifacts,
        test_summary=test_summary,
        acceptance_results=acceptance_results,
        safety_flags={
            "release_hold": RELEASE_HOLD_VALUE,
            "advisory_only": True,
            "human_review_required": True,
            **SAFETY_FLAGS,
        },
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    # Also write closeout data as JSON
    closeout_data = build_closeout_data(
        verdict=args.verdict,
        seed=args.seed,
        artifacts=artifacts,
        total_artifacts=len(artifacts),
    )
    (quality_dir / "closeout_data.json").write_text(
        json.dumps(closeout_data, sort_keys=True, indent=2)
    )

    print(f"Closeout generated: {output_path}")
    print(f"Verdict: {args.verdict}")
    print(f"Artifacts: {len(artifacts)}/{len(REQUIRED_ARTIFACTS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
