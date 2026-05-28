#!/usr/bin/env python3
"""Build offline research result catalog.

Scans explicit offline output dirs for research artifacts.
Never imports, executes, stages, or modifies any file.

Usage:
    python3 scripts/build_offline_research_result_catalog.py \
        --output-dir /tmp/offline_research_result_catalog \
        --strict \
        --release-hold HOLD
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from core.offline_research_result_catalog import (
    RELEASE_HOLD_REQUIRED,
    scan_artifacts,
    validate_release_hold,
    write_json,
    write_manifest,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build offline research result catalog")
    parser.add_argument("--output-dir", default="/tmp/offline_research_result_catalog")
    parser.add_argument("--release-hold", default=RELEASE_HOLD_REQUIRED)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--scan-dirs", default=None, help="JSON file with dir list")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.strict and args.release_hold != RELEASE_HOLD_REQUIRED:
        print(f"FAIL: release_hold={args.release_hold!r} != {RELEASE_HOLD_REQUIRED!r}", file=sys.stderr)
        return 1

    scan_dirs = None
    if args.scan_dirs:
        p = pathlib.Path(args.scan_dirs)
        if p.exists():
            scan_dirs = json.loads(p.read_text(encoding="utf-8"))

    catalog = scan_artifacts(scan_dirs, release_hold=args.release_hold)

    out_dir = pathlib.Path(args.output_dir)
    write_json(catalog, out_dir / "result_catalog.json")
    write_manifest(catalog, out_dir / "result_catalog_manifest.json")
    write_markdown(catalog, out_dir / "result_catalog.md")

    print(f"OK: {len(catalog.artifacts)} artifacts cataloged")
    print(f"    scanned: {len(catalog.scanned_dirs)} dirs")
    print(f"    missing: {len(catalog.missing_dirs)} dirs")
    print(f"    release_hold={catalog.manifest['release_hold']}")
    print(f"    output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
