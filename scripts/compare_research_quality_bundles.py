#!/usr/bin/env python3
"""Compare research quality bundles — verify deterministic equivalence.

Usage:
    python3 scripts/compare_research_quality_bundles.py \
        --left /tmp/multi_strategy_research_quality_gate \
        --right /tmp/multi_strategy_research_quality_gate_rerun \
        --require-identical-hashes \
        --allow-timestamp-fields generated_at

Safety: offline only, no network.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.research_rerun_diff import detect_rerun_diff
from core.research_artifact_hashing import TIMESTAMP_ALLOWLIST
from core.research_quality_manifest import REQUIRED_ARTIFACTS


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare research quality bundles")
    parser.add_argument("--left", required=True, help="Left bundle directory")
    parser.add_argument("--right", required=True, help="Right bundle directory")
    parser.add_argument("--require-identical-hashes", action="store_true")
    parser.add_argument("--allow-timestamp-fields", default="generated_at",
                        help="Comma-separated timestamp fields to allowlist")
    args = parser.parse_args()

    left = Path(args.left)
    right = Path(args.right)

    if not left.exists():
        print(f"FAIL: left directory missing: {left}", file=sys.stderr)
        return 2
    if not right.exists():
        print(f"FAIL: right directory missing: {right}", file=sys.stderr)
        return 2

    allowlist = tuple(f.strip() for f in args.allow_timestamp_fields.split(","))
    full_allowlist = TIMESTAMP_ALLOWLIST + allowlist

    result = detect_rerun_diff(left, right, REQUIRED_ARTIFACTS, full_allowlist)

    if result["identical"]:
        print("PASS: Bundles are identical (excluding allowlisted timestamp fields)")
        return 0

    if args.require_identical_hashes and not result["identical"]:
        print("FAIL: Bundles differ")
        for k, v in result.get("differences", {}).items():
            print(f"  DIFF: {k}: left={v['left'][:16]}... right={v['right'][:16]}...")
        for m in result.get("missing", []):
            print(f"  MISSING: {m}")
        return 2

    print("PARTIAL: Bundles differ but --require-identical-hashes not set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
