#!/usr/bin/env python3
"""Build frozen backup evidence checklist from backup manifest + archive simulation.

Never performs actual backup/archive/delete operations.

Usage:
    PYTHONPATH=. python3 scripts/build_frozen_backup_evidence_checklist.py \
        --backup-manifest-dir /tmp/frozen_backup_manifest \
        --archive-simulation-dir /tmp/frozen_archive_simulation \
        --output-dir /tmp/frozen_backup_evidence_checklist \
        --strict \
        --release-hold HOLD
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from core.frozen_backup_evidence_checklist import (
    RELEASE_HOLD_REQUIRED,
    build_evidence_checklist,
    load_manifest_items,
    load_sim_items,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frozen backup evidence checklist")
    parser.add_argument("--backup-manifest-dir", required=True)
    parser.add_argument("--archive-simulation-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_backup_evidence_checklist")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    manifest_path = pathlib.Path(args.backup_manifest_dir) / "backup_manifest.json"
    sim_path = pathlib.Path(args.archive_simulation_dir) / "archive_simulation.json"

    if not manifest_path.exists():
        print(f"FAIL: {manifest_path} not found.", file=sys.stderr)
        return 1
    if not sim_path.exists():
        print(f"FAIL: {sim_path} not found.", file=sys.stderr)
        return 1

    manifest_items = load_manifest_items(manifest_path)
    sim_items = load_sim_items(sim_path)
    checklist_items = build_evidence_checklist(manifest_items, sim_items, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    write_json(checklist_items, out_dir / "backup_evidence_checklist.json")
    write_manifest(checklist_items, out_dir / "backup_evidence_checklist_manifest.json", args.release_hold)
    write_markdown(checklist_items, out_dir / "backup_evidence_checklist.md")

    print(f"OK: {len(checklist_items)} evidence checklist items built")
    print(f"    manifest release_hold={args.release_hold}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
