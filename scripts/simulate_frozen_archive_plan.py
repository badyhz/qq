#!/usr/bin/env python3
"""Simulate frozen archive plan from backup manifest.

Reads backup_manifest.json. Never performs actual archive/delete/move.

Usage:
    PYTHONPATH=. python3 scripts/simulate_frozen_archive_plan.py \
        --backup-manifest-dir /tmp/frozen_backup_manifest \
        --output-dir /tmp/frozen_archive_simulation \
        --strict \
        --release-hold HOLD
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from core.frozen_archive_simulation import (
    RELEASE_HOLD_REQUIRED,
    build_archive_simulation,
    load_backup_manifest,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate frozen archive plan")
    parser.add_argument("--backup-manifest-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_archive_simulation")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    manifest_path = pathlib.Path(args.backup_manifest_dir) / "backup_manifest.json"
    if not manifest_path.exists():
        print(f"FAIL: {manifest_path} not found.", file=sys.stderr)
        return 1

    backup_items = load_backup_manifest(manifest_path)
    sim_items = build_archive_simulation(backup_items, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    write_json(sim_items, out_dir / "archive_simulation.json")
    write_manifest(sim_items, out_dir / "archive_simulation_manifest.json", args.release_hold)
    write_markdown(sim_items, out_dir / "archive_simulation.md")

    print(f"OK: {len(sim_items)} archive simulation items built")
    print(f"    manifest release_hold={args.release_hold}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
