#!/usr/bin/env python3
"""Build frozen backup manifest from decision prep + inventory.

Reads archive_delete_decision_prep.json and frozen_inventory.json.
Never performs actual backup operations.

Usage:
    PYTHONPATH=. python3 scripts/build_frozen_backup_manifest.py \
        --decision-prep-dir /tmp/frozen_archive_delete_decision_prep \
        --inventory-dir /tmp/frozen_inventory_review \
        --output-dir /tmp/frozen_backup_manifest \
        --strict \
        --release-hold HOLD
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from core.frozen_backup_manifest import (
    RELEASE_HOLD_REQUIRED,
    build_backup_manifest,
    load_decision_prep,
    load_inventory_files,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen backup manifest")
    parser.add_argument("--decision-prep-dir", required=True)
    parser.add_argument("--inventory-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_backup_manifest")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    prep_path = pathlib.Path(args.decision_prep_dir) / "archive_delete_decision_prep.json"
    inv_path = pathlib.Path(args.inventory_dir) / "frozen_inventory.json"

    if not prep_path.exists():
        print(f"FAIL: {prep_path} not found.", file=sys.stderr)
        return 1
    if not inv_path.exists():
        print(f"FAIL: {inv_path} not found.", file=sys.stderr)
        return 1

    prep_items = load_decision_prep(prep_path)
    inv_files = load_inventory_files(inv_path)
    manifest_items = build_backup_manifest(prep_items, inv_files, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    write_json(manifest_items, out_dir / "backup_manifest.json")
    write_manifest(manifest_items, out_dir / "backup_manifest_manifest.json", args.release_hold)
    write_markdown(manifest_items, out_dir / "backup_manifest.md")

    print(f"OK: {len(manifest_items)} backup manifest items built")
    print(f"    manifest release_hold={args.release_hold}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
