#!/usr/bin/env python3
"""Compare research artifact browsers — diff two browser outputs.

Usage:
    python3 scripts/compare_research_artifact_browsers.py \
        --left /tmp/research_artifact_browser \
        --right /tmp/research_artifact_browser_rerun \
        --output-dir /tmp/research_artifact_browser_compare \
        --require-identical-safety-flags

Safety: offline only. No network. No exchange.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.research_artifact_compare import (
    compare_browser_outputs,
    comparison_to_dict,
    comparison_to_json,
    comparison_to_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare research artifact browsers")
    parser.add_argument("--left", required=True, help="Left browser output directory")
    parser.add_argument("--right", required=True, help="Right browser output directory")
    parser.add_argument("--output-dir", required=True, help="Comparison output directory")
    parser.add_argument("--require-identical-safety-flags", action="store_true",
                        help="FAIL if safety flags differ")
    args = parser.parse_args()

    left = Path(args.left)
    right = Path(args.right)
    output_dir = Path(args.output_dir)

    if not left.exists():
        print(f"FAIL: left directory missing: {left}", file=sys.stderr)
        return 2
    if not right.exists():
        print(f"FAIL: right directory missing: {right}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)

    result = compare_browser_outputs(
        left, right,
        require_identical_safety_flags=args.require_identical_safety_flags,
    )

    # Write diff JSON
    diff_dict = comparison_to_dict(result)
    (output_dir / "artifact_browser_diff.json").write_text(
        json.dumps(diff_dict, sort_keys=True, indent=2)
    )

    # Write diff markdown
    diff_md = comparison_to_markdown(result)
    (output_dir / "artifact_browser_diff.md").write_text(diff_md)

    # Summary
    print(f"{result.status}: "
          f"safety={'IDENTICAL' if result.identical_safety_flags else 'DIFFERENT'} "
          f"verdict={'IDENTICAL' if result.identical_verdict else 'DIFFERENT'} "
          f"changed={len(result.changed_artifacts)} "
          f"added={len(result.added_artifacts)} "
          f"removed={len(result.removed_artifacts)}")

    if result.status == "FAIL":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
