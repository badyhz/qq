#!/usr/bin/env python3
"""Build frozen archive/delete decision prep from human review queue.

Reads human_review_queue.json.  Never performs actual file operations.

Usage:
    PYTHONPATH=. python3 scripts/build_frozen_archive_delete_decision_prep.py \
        --human-review-queue-dir /tmp/frozen_human_review_queue \
        --output-dir /tmp/frozen_archive_delete_decision_prep \
        --strict \
        --release-hold HOLD
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from core.frozen_archive_delete_decision_prep import (
    RELEASE_HOLD_REQUIRED,
    build_decision_prep,
    load_queue,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen archive/delete decision prep")
    parser.add_argument("--human-review-queue-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_archive_delete_decision_prep")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    queue_path = pathlib.Path(args.human_review_queue_dir) / "human_review_queue.json"
    if not queue_path.exists():
        print(f"FAIL: {queue_path} not found. Regenerate human review queue first.", file=sys.stderr)
        return 1

    queue_items = load_queue(queue_path)
    prep_items = build_decision_prep(queue_items, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    write_json(prep_items, out_dir / "archive_delete_decision_prep.json")
    write_manifest(prep_items, out_dir / "archive_delete_decision_prep_manifest.json", args.release_hold)
    write_markdown(prep_items, out_dir / "archive_delete_decision_prep.md")

    print(f"OK: {len(prep_items)} decision prep items built")
    print(f"    manifest release_hold={args.release_hold}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
