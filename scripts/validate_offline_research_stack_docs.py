#!/usr/bin/env python3
"""Validate offline research stack documentation governance.

No network. No exchange. No runtime. No planner. Advisory only.
release_hold must remain HOLD.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.offline_research_governance_manifest import emit_governance_validation


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate offline research stack documentation governance"
    )
    parser.add_argument(
        "--docs-root", required=True, type=Path,
        help="Root directory of docs"
    )
    parser.add_argument(
        "--output-dir", required=True, type=Path,
        help="Output directory for governance validation results"
    )
    parser.add_argument(
        "--strict", action="store_true", default=False,
        help="Enable strict validation mode"
    )
    parser.add_argument(
        "--release-hold", default="HOLD", type=str,
        help="Expected release_hold value (must be HOLD)"
    )
    args = parser.parse_args()

    if args.release_hold != "HOLD":
        print(f"ERROR: release_hold must be HOLD, got {args.release_hold}", file=sys.stderr)
        return 1

    if not args.docs_root.is_dir():
        print(f"ERROR: Docs root not found: {args.docs_root}", file=sys.stderr)
        return 1

    result = emit_governance_validation(
        docs_root=args.docs_root,
        output_dir=args.output_dir,
        release_hold=args.release_hold,
    )

    if result["valid"]:
        print(f"PASS: Governance validation passed")
        print(f"  Artifacts: {result['validation_json']}, {result['validation_md']}, {result['manifest_json']}")
        return 0
    else:
        print(f"FAIL: Governance validation failed ({len(result['errors'])} errors)", file=sys.stderr)
        for err in result["errors"]:
            print(f"  - {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
