#!/usr/bin/env python3
"""Verify frozen backup manifest and archive simulation safety.

Reads backup_manifest.json and archive_simulation.json.
Checks all safety invariants.

Usage:
    PYTHONPATH=. python3 scripts/verify_frozen_backup_manifest.py \
        --backup-manifest-dir /tmp/frozen_backup_manifest \
        --archive-simulation-dir /tmp/frozen_archive_simulation \
        --output-dir /tmp/frozen_backup_verification \
        --strict \
        --release-hold HOLD
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from core.frozen_backup_verification import (
    RELEASE_HOLD_REQUIRED,
    load_json,
    verify_backup_manifest,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify frozen backup manifest")
    parser.add_argument("--backup-manifest-dir", required=True)
    parser.add_argument("--archive-simulation-dir", required=True)
    parser.add_argument("--output-dir", default="/tmp/frozen_backup_verification")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    backup_path = pathlib.Path(args.backup_manifest_dir) / "backup_manifest.json"
    sim_path = pathlib.Path(args.archive_simulation_dir) / "archive_simulation.json"

    if args.strict and not backup_path.exists():
        print(f"FAIL: {backup_path} not found.", file=sys.stderr)
        return 1
    if args.strict and not sim_path.exists():
        print(f"FAIL: {sim_path} not found.", file=sys.stderr)
        return 1

    backup_data = load_json(backup_path) if backup_path.exists() else []
    sim_data = load_json(sim_path) if sim_path.exists() else []

    report = verify_backup_manifest(backup_data, sim_data, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    write_json(report, out_dir / "backup_verification.json")
    write_manifest(report, out_dir / "backup_verification_manifest.json")
    write_markdown(report, out_dir / "backup_verification.md")

    status = "PASS" if report.all_passed else "FAIL"
    print(f"{status}: {report.passed_checks}/{report.total_checks} checks passed")
    print(f"    output: {out_dir}")
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
