#!/usr/bin/env python3
"""Build frozen approval outcome matrix.

Builds outcome matrix from dry-run validation results. No actual approval.

Usage:
    PYTHONPATH=. python3 scripts/build_frozen_approval_outcome_matrix.py \
        --dry-run-validation-dir /tmp/frozen_approval_dry_run_validation \
        --output-dir /tmp/frozen_approval_outcome_matrix \
        --strict \
        --release-hold HOLD
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from core.frozen_approval_outcome_matrix import (
    RELEASE_HOLD_REQUIRED,
    build_outcome_matrix,
    render_manifest,
    render_matrix_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen approval outcome matrix")
    parser.add_argument("--dry-run-validation-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_approval_outcome_matrix")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    val_path = pathlib.Path(args.dry_run_validation_dir) / "dry_run_validation.json"
    if not val_path.exists():
        print(f"FAIL: {val_path} not found.", file=sys.stderr)
        return 1

    data = json.loads(val_path.read_text(encoding="utf-8"))
    results = data.get("results", data) if isinstance(data, dict) else data

    matrix = build_outcome_matrix(results, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "approval_outcome_matrix.json").write_text(
        json.dumps(matrix.to_dict(), indent=2), encoding="utf-8"
    )
    (out_dir / "approval_outcome_matrix.md").write_text(
        render_matrix_markdown(matrix), encoding="utf-8"
    )
    (out_dir / "approval_outcome_matrix_manifest.json").write_text(
        json.dumps(render_manifest(matrix), indent=2), encoding="utf-8"
    )

    print(f"OK: {matrix.total_forms} forms, {matrix.total_outcomes} outcome categories")
    print(f"    release_hold={args.release_hold}")
    print(f"    action_authorized={matrix.action_authorized}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
