#!/usr/bin/env python3
"""Build frozen inventory archive plan (no-touch migration design).

Reads decision_matrix.json and produces a future proposed action plan.
Never moves, deletes, renames, modifies, stages, or executes any file.

Usage:
    python3 scripts/build_frozen_inventory_archive_plan.py \
        --decision-matrix-dir /tmp/frozen_inventory_decision_matrix \
        --output-dir /tmp/frozen_inventory_archive_plan \
        --strict \
        --release-hold HOLD
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from core.frozen_inventory_archive_plan import (
    RELEASE_HOLD_REQUIRED,
    build_archive_plan,
    validate_no_forbidden_actions,
    validate_no_touch,
    validate_release_hold,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen inventory archive plan")
    parser.add_argument("--decision-matrix-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_inventory_archive_plan")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    dm_path = pathlib.Path(args.decision_matrix_dir) / "decision_matrix.json"
    if not dm_path.exists():
        print(f"FAIL: {dm_path} not found", file=sys.stderr)
        return 1

    matrix_data = json.loads(dm_path.read_text(encoding="utf-8"))
    plan = build_archive_plan(matrix_data)

    if args.strict:
        violations = validate_no_forbidden_actions(plan)
        if violations:
            print(f"FAIL: forbidden actions: {violations}", file=sys.stderr)
            return 1
        touch_violations = validate_no_touch(plan)
        if touch_violations:
            print(f"FAIL: no-touch violations: {touch_violations}", file=sys.stderr)
            return 1

    out_dir = pathlib.Path(args.output_dir)
    write_json(plan, out_dir / "archive_plan.json")
    write_manifest(plan, out_dir / "archive_plan_manifest.json")
    write_markdown(plan, out_dir / "archive_plan.md")

    print(f"OK: {len(plan.entries)} entries in archive plan")
    print(f"    release_hold={plan.manifest['release_hold']}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
