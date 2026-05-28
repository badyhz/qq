#!/usr/bin/env python3
"""Build frozen inventory human decision matrix.

Reads frozen_inventory.json and produces a human disposition matrix.
Never imports, executes, stages, or modifies any frozen file.

Usage:
    python3 scripts/build_frozen_inventory_decision_matrix.py \
        --inventory-dir /tmp/frozen_inventory_review \
        --output-dir /tmp/frozen_inventory_decision_matrix \
        --strict \
        --release-hold HOLD
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from core.frozen_inventory_decision_matrix import (
    RELEASE_HOLD_REQUIRED,
    build_decision_matrix,
    validate_no_forbidden_markers,
    validate_release_hold,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen inventory decision matrix")
    parser.add_argument("--inventory-dir", required=True, help="Dir containing frozen_inventory.json")
    parser.add_argument("--output-dir", default="/tmp/frozen_inventory_decision_matrix")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    inv_path = pathlib.Path(args.inventory_dir) / "frozen_inventory.json"
    if not inv_path.exists():
        print(f"FAIL: {inv_path} not found", file=sys.stderr)
        return 1

    inventory_data = json.loads(inv_path.read_text(encoding="utf-8"))
    matrix = build_decision_matrix(inventory_data)

    if args.strict:
        violations = validate_no_forbidden_markers(matrix)
        if violations:
            print(f"FAIL: forbidden markers found: {violations}", file=sys.stderr)
            return 1

    out_dir = pathlib.Path(args.output_dir)
    write_json(matrix, out_dir / "decision_matrix.json")
    write_manifest(matrix, out_dir / "decision_matrix_manifest.json")
    write_markdown(matrix, out_dir / "decision_matrix.md")

    print(f"OK: {len(matrix.entries)} entries in decision matrix")
    print(f"    release_hold={matrix.manifest['release_hold']}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
