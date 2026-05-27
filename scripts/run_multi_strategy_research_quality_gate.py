#!/usr/bin/env python3
"""Run multi-strategy research quality gate — one-shot full quality gate CLI.

Usage:
    python3 scripts/run_multi_strategy_research_quality_gate.py \
        --input-dir /tmp/multi_strategy_research_workbench \
        --output-dir /tmp/multi_strategy_research_quality_gate \
        --min-oos-splits 3 \
        --min-stability-score 0.60 \
        --max-parameter-fragility 0.40 \
        --max-overlap-risk 0.70 \
        --min-negative-control-margin 0.10 \
        --bootstrap-iterations 200 \
        --deterministic-seed 424242 \
        --require-negative-control \
        --require-regime-breakdown \
        --require-bootstrap \
        --require-reproducibility \
        --strict \
        --release-hold HOLD

Safety: offline only, no network, no exchange, no runtime, no planner.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.research_quality_gate_v2 import run_quality_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multi-strategy research quality gate")
    parser.add_argument("--input-dir", required=True, help="Workbench output directory")
    parser.add_argument("--output-dir", required=True, help="Quality gate output directory")
    parser.add_argument("--min-oos-splits", type=int, default=3)
    parser.add_argument("--min-stability-score", type=float, default=0.60)
    parser.add_argument("--max-parameter-fragility", type=float, default=0.40)
    parser.add_argument("--max-overlap-risk", type=float, default=0.70)
    parser.add_argument("--min-negative-control-margin", type=float, default=0.10)
    parser.add_argument("--bootstrap-iterations", type=int, default=200)
    parser.add_argument("--deterministic-seed", type=int, default=424242)
    parser.add_argument("--require-negative-control", action="store_true")
    parser.add_argument("--require-regime-breakdown", action="store_true")
    parser.add_argument("--require-bootstrap", action="store_true")
    parser.add_argument("--require-reproducibility", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--release-hold", default="HOLD")
    args = parser.parse_args()

    if args.release_hold != "HOLD":
        print("FAIL: release_hold must be HOLD", file=sys.stderr)
        return 2

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"FAIL: input directory does not exist: {input_dir}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)

    try:
        result = run_quality_gate(
            input_dir=input_dir,
            output_dir=output_dir,
            seed=args.deterministic_seed,
            strict=args.strict,
            release_hold=args.release_hold,
            min_oos_splits=args.min_oos_splits,
            min_stability_score=args.min_stability_score,
            max_parameter_fragility=args.max_parameter_fragility,
            max_overlap_risk=args.max_overlap_risk,
            min_negative_control_margin=args.min_negative_control_margin,
            bootstrap_iterations=args.bootstrap_iterations,
            require_negative_control=args.require_negative_control,
            require_regime_breakdown=args.require_regime_breakdown,
            require_bootstrap=args.require_bootstrap,
            require_reproducibility=args.require_reproducibility,
        )
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 2

    print(f"Quality gate complete: {result['verdict']}")
    print(f"  Composite score: {result['composite_score']:.4f}")
    print(f"  Evidence completeness: {result['evidence_completeness']:.4f}")
    print(f"  Artifacts written: {result['artifacts_written']}")
    print(f"  Hard blocks: {result['hard_blocks']}")
    print(f"  Warnings: {result['warnings']}")

    if result["verdict"] == "FAIL":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
