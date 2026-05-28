#!/usr/bin/env python3
"""Build frozen human review queue from decision matrix.

Reads decision_matrix.json.  Never imports or executes frozen files.

Usage:
    PYTHONPATH=. python3 scripts/build_frozen_human_review_queue.py \
        --decision-matrix-dir /tmp/frozen_inventory_decision_matrix \
        --output-dir /tmp/frozen_human_review_queue \
        --strict \
        --release-hold HOLD
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from core.frozen_human_review_queue import (
    RELEASE_HOLD_REQUIRED,
    build_queue_from_matrix,
    load_decision_matrix,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen human review queue")
    parser.add_argument("--decision-matrix-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_human_review_queue")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    matrix_path = pathlib.Path(args.decision_matrix_dir) / "decision_matrix.json"
    if not matrix_path.exists():
        print(f"FAIL: {matrix_path} not found. Regenerate decision matrix first.", file=sys.stderr)
        return 1

    entries = load_decision_matrix(matrix_path)
    items = build_queue_from_matrix(entries, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    write_json(items, out_dir / "human_review_queue.json")
    write_manifest(items, out_dir / "human_review_queue_manifest.json", args.release_hold)
    write_markdown(items, out_dir / "human_review_queue.md")

    print(f"OK: {len(items)} queue items built")
    print(f"    manifest release_hold={args.release_hold}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
