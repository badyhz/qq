#!/usr/bin/env python3
"""Run offline governance regression pack.

Orchestrates key offline governance checks in sequence.
No network. No exchange. No runtime. No planner.

Usage:
    python3 scripts/run_offline_governance_regression_pack.py \
        --output-dir /tmp/offline_governance_regression_pack \
        --strict \
        --release-hold HOLD
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from core.offline_governance_regression_pack import (
    RELEASE_HOLD_REQUIRED,
    run_regression_pack,
    validate_release_hold,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline governance regression pack")
    parser.add_argument("--output-dir", default="/tmp/offline_governance_regression_pack")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    pack = run_regression_pack(repo_root=repo_root, release_hold=args.release_hold, timeout=args.timeout)

    if args.strict and pack.final_verdict == "FAIL":
        print(f"FAIL: regression pack verdict={pack.final_verdict}", file=sys.stderr)

    out_dir = pathlib.Path(args.output_dir)
    write_json(pack, out_dir / "regression_pack.json")
    write_manifest(pack, out_dir / "regression_pack_manifest.json")
    write_markdown(pack, out_dir / "regression_pack.md")

    print(f"OK: {len(pack.checks)} checks run")
    print(f"    verdict: {pack.final_verdict}")
    print(f"    release_hold={pack.manifest['release_hold']}")
    print(f"    output: {out_dir}")

    if args.strict and pack.final_verdict == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
